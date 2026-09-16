"""``karte_notify``（Issue #512）の単体テスト。

対象: 通知要否の判定ロジック（:mod:`karte_notify.notify`）と PostToolUse フックの実体
（:mod:`karte_notify.hook`）。カルテ実体（``tmp/_karte/issue-<N>.md``）を経由せず、
``karte status --json`` の出力形（``karte/cli.py::_status_payload``）を模した dict を直接
使うことで、決定論的に全ての判定表の行を固定する。
"""

import io
import json
import tempfile
import unittest
from pathlib import Path

from karte_notify import hook, notify


def finding(fid, status, *, harm="real", disposition="fix-here", summary="dummy"):
    return {
        "id": fid,
        "status": status,
        "harm": harm,
        "severity": "major",
        "scope": "in",
        "disposition": disposition,
        "summary": summary,
    }


def payload(issue, *, verdict="clean", escalate=False, findings=None):
    return {
        "issue": issue,
        "verdict": verdict,
        "escalate": escalate,
        "findings": findings or [],
    }


class DetectTriggerTests(unittest.TestCase):
    def test_matches_ingest_review(self):
        self.assertEqual(
            notify.detect_trigger("python3 -m karte ingest-review --issue 512 --round 1 --from -"),
            "ingest-review",
        )

    def test_matches_close_attempt(self):
        self.assertEqual(
            notify.detect_trigger("python3 -m karte close-attempt --issue 512 --outcome fixed"),
            "close-attempt",
        )

    def test_matches_python_without_trailing_digit(self):
        self.assertEqual(
            notify.detect_trigger("python -m karte ingest-review --issue 1 --round 1 --from -"),
            "ingest-review",
        )

    def test_no_match_for_other_verbs(self):
        self.assertIsNone(notify.detect_trigger("python3 -m karte status --issue 512 --json"))
        self.assertIsNone(notify.detect_trigger("python3 -m karte render --issue 512"))
        self.assertIsNone(notify.detect_trigger("python3 -m karte append --issue 512"))

    def test_no_match_for_unrelated_command(self):
        self.assertIsNone(notify.detect_trigger("gh pr create --title x --body y"))

    def test_word_boundary_rejects_suffixed_verb(self):
        # `close-attempt2` のような偽の一致を作らない（\b の境界検査）。
        self.assertIsNone(notify.detect_trigger("python3 -m karte close-attempt2 --issue 1"))


class IssueFromCommandTests(unittest.TestCase):
    def test_extracts_issue_number(self):
        self.assertEqual(
            notify.issue_from_command("python3 -m karte ingest-review --issue 512 --round 1"),
            512,
        )

    def test_extracts_with_equals_form(self):
        self.assertEqual(
            notify.issue_from_command("python3 -m karte close-attempt --issue=512 --outcome fixed"),
            512,
        )

    def test_returns_none_when_absent(self):
        self.assertIsNone(notify.issue_from_command("python3 -m karte close-attempt --outcome fixed"))

    def test_returns_none_for_invalid_issue(self):
        self.assertIsNone(notify.issue_from_command("python3 -m karte ingest-review --issue 0"))


class SnapshotPathTests(unittest.TestCase):
    def test_round_trip_read_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tmp" / "_karte").mkdir(parents=True)
            path = notify.notified_snapshot_path(root, 512, create_dir=True)
            self.assertEqual(path, root / "tmp" / "_karte" / "notified" / "issue-512.json")
            self.assertIsNone(notify.read_snapshot(path))

            snapshot = {"issue": 512, "findings": {"F-512-01": "open"}, "verdict": "harmful-open", "escalate": False}
            notify.write_snapshot(path, snapshot)
            self.assertEqual(notify.read_snapshot(path), snapshot)

    def test_read_snapshot_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "tmp" / "_karte" / "notified" / "issue-1.json"
            self.assertIsNone(notify.read_snapshot(path))


class DecideTests(unittest.TestCase):
    """Issue #512 本文「通知条件」の判定表を1行ずつ固定する。"""

    def test_first_run_shows_everything_even_when_clean(self):
        message, snapshot = notify.decide(payload(512), previous=None)
        assert message is not None
        self.assertIn("初回通知", message)
        self.assertEqual(snapshot, {"issue": 512, "findings": {}, "verdict": "clean", "escalate": False})

    def test_open_finding_always_shown_regardless_of_prior_state(self):
        current = payload(512, verdict="harmful-open", findings=[finding("F-512-01", "open")])
        for previous in (
            None,
            {"findings": {"F-512-01": "open"}, "verdict": "harmful-open", "escalate": False},
            {"findings": {}, "verdict": "clean", "escalate": False},
        ):
            with self.subTest(previous=previous):
                message, _ = notify.decide(current, previous)
                assert message is not None
                self.assertIn("F-512-01", message)

    def test_resolved_after_open_is_shown_exactly_once(self):
        current = payload(512, verdict="clean", findings=[finding("F-512-01", "resolved")])
        previous = {"findings": {"F-512-01": "open"}, "verdict": "harmful-open", "escalate": False}
        message, snapshot = notify.decide(current, previous)
        assert message is not None
        self.assertIn("F-512-01", message)
        self.assertEqual(snapshot["findings"]["F-512-01"], "resolved")

        # 次回、同じ resolved 状態が続く限りもう載らない。
        message2, _ = notify.decide(current, snapshot)
        self.assertIsNone(message2)

    def test_resolved_when_unnotified_before_is_shown_once(self):
        current = payload(512, verdict="clean", findings=[finding("F-512-01", "resolved")])
        # 未通知（スナップショットはあるが当該 finding 自体が未収載）。
        previous = {"findings": {}, "verdict": "clean", "escalate": False}
        message, _ = notify.decide(current, previous)
        assert message is not None
        self.assertIn("F-512-01", message)

    def test_resolved_twice_in_a_row_is_silent(self):
        current = payload(512, verdict="clean", findings=[finding("F-512-01", "resolved")])
        previous = {"findings": {"F-512-01": "resolved"}, "verdict": "clean", "escalate": False}
        message, snapshot = notify.decide(current, previous)
        self.assertIsNone(message)
        self.assertEqual(snapshot["findings"]["F-512-01"], "resolved")

    def test_escalate_continues_to_be_shown_every_time(self):
        current = payload(512, verdict="harmful-open", escalate=True, findings=[finding("F-512-01", "open")])
        previous = {"findings": {"F-512-01": "open"}, "verdict": "harmful-open", "escalate": True}
        message, _ = notify.decide(current, previous)
        assert message is not None
        self.assertIn("escalate: yes", message)

    def test_escalate_continuation_without_finding_or_verdict_change(self):
        """escalate: yes の継続は、finding も verdict も変化していなくても毎回載る。"""
        current = payload(512, verdict="harmful-open", escalate=True, findings=[finding("F-512-01", "resolved")])
        previous = {"findings": {"F-512-01": "resolved"}, "verdict": "harmful-open", "escalate": True}
        message, _ = notify.decide(current, previous)
        assert message is not None
        self.assertIn("escalate: yes", message)
        self.assertIn("継続", message)

    def test_verdict_change_with_no_findings_is_shown_header_only(self):
        current = payload(512, verdict="clean", escalate=False, findings=[])
        previous = {"findings": {}, "verdict": "no-harm-only", "escalate": False}
        message, _ = notify.decide(current, previous)
        assert message is not None
        self.assertIn("verdict の変化のみ", message)

    def test_no_findings_and_no_change_is_silent(self):
        current = payload(512, verdict="clean", escalate=False, findings=[finding("F-512-01", "resolved")])
        previous = {"findings": {"F-512-01": "resolved"}, "verdict": "clean", "escalate": False}
        message, _ = notify.decide(current, previous)
        self.assertIsNone(message)


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class HookRunTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        (self.root / "tmp" / "_karte").mkdir(parents=True)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.runner_calls = []

    def runner_returning(self, payload_dict, *, returncode=0):
        def run(argv, **kwargs):
            self.runner_calls.append(list(argv))
            return FakeCompleted(returncode, json.dumps(payload_dict))

        return run

    def invoke(self, tool_payload, runner):
        stdin = io.StringIO(json.dumps(tool_payload))
        return hook.run(
            stdin=stdin, stdout=self.stdout, stderr=self.stderr,
            project_root=self.root, runner=runner,
        )

    def test_non_bash_tool_is_ignored(self):
        code = self.invoke({"tool_name": "Write", "tool_input": {"file_path": "x"}}, self.runner_returning({}))
        self.assertEqual(code, 0)
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertEqual(self.runner_calls, [])

    def test_non_matching_bash_command_is_ignored(self):
        code = self.invoke(
            {"tool_name": "Bash", "tool_input": {"command": "gh pr create --title x --body y"}},
            self.runner_returning({}),
        )
        self.assertEqual(code, 0)
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertEqual(self.runner_calls, [])

    def test_ingest_review_first_run_emits_system_message(self):
        status = payload(512, verdict="harmful-open", findings=[finding("F-512-01", "open")])
        code = self.invoke(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "python3 -m karte ingest-review --issue 512 --round 1 --from -"
                },
            },
            self.runner_returning(status),
        )
        self.assertEqual(code, 0)
        self.assertTrue(self.runner_calls)
        decision = json.loads(self.stdout.getvalue())
        self.assertIn("F-512-01", decision["systemMessage"])
        snapshot_path = self.root / "tmp" / "_karte" / "notified" / "issue-512.json"
        self.assertTrue(snapshot_path.is_file())

    def test_second_call_with_unchanged_open_finding_still_notifies(self):
        status = payload(512, verdict="harmful-open", findings=[finding("F-512-01", "open")])
        tool_payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m karte close-attempt --issue 512 --outcome partial"},
        }
        self.invoke(tool_payload, self.runner_returning(status))
        self.stdout = io.StringIO()
        code = self.invoke(tool_payload, self.runner_returning(status))
        self.assertEqual(code, 0)
        decision = json.loads(self.stdout.getvalue())
        self.assertIn("F-512-01", decision["systemMessage"])

    def test_resolved_twice_in_a_row_is_silent_end_to_end(self):
        open_status = payload(512, verdict="harmful-open", findings=[finding("F-512-01", "open")])
        resolved_status = payload(512, verdict="clean", findings=[finding("F-512-01", "resolved")])
        tool_payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m karte close-attempt --issue 512 --outcome fixed"},
        }
        self.invoke(tool_payload, self.runner_returning(open_status))
        self.stdout = io.StringIO()
        self.invoke(tool_payload, self.runner_returning(resolved_status))
        first_resolved_message = json.loads(self.stdout.getvalue())["systemMessage"]
        self.assertIn("F-512-01", first_resolved_message)

        self.stdout = io.StringIO()
        code = self.invoke(tool_payload, self.runner_returning(resolved_status))
        self.assertEqual(code, 0)
        self.assertEqual(self.stdout.getvalue(), "")

    def test_status_command_failure_is_silent_and_safe(self):
        code = self.invoke(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "python3 -m karte ingest-review --issue 512 --round 1 --from -"},
            },
            self.runner_returning({}, returncode=4),
        )
        self.assertEqual(code, 0)
        self.assertEqual(self.stdout.getvalue(), "")

    def test_manual_status_invocation_is_untouched_by_hook(self):
        # `karte status` 自体の実行は本フックの検出対象外（手動実行は毎回全件を出す・AC）。
        code = self.invoke(
            {"tool_name": "Bash", "tool_input": {"command": "python3 -m karte status --issue 512"}},
            self.runner_returning({}),
        )
        self.assertEqual(code, 0)
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertEqual(self.runner_calls, [])


if __name__ == "__main__":
    unittest.main()
