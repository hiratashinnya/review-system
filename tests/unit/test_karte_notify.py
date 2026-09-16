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


class ExtractCommandsTests(unittest.TestCase):
    """Issue #512 是正（F-512-02）: tool_name ごとのコマンド抽出を固定する。"""

    def test_bash_extracts_single_command(self):
        self.assertEqual(
            notify.extract_commands("Bash", {"command": "python3 -m karte close-attempt --issue 1"}),
            ["python3 -m karte close-attempt --issue 1"],
        )

    def test_ctx_execute_extracts_code(self):
        self.assertEqual(
            notify.extract_commands(
                "mcp__plugin_context-mode_context-mode__ctx_execute",
                {
                    "language": "shell",
                    "code": "python3 -m karte ingest-review --issue 1 --round 1 --from -",
                },
            ),
            ["python3 -m karte ingest-review --issue 1 --round 1 --from -"],
        )

    def test_ctx_batch_execute_extracts_all_commands(self):
        commands = notify.extract_commands(
            "mcp__plugin_context-mode_context-mode__ctx_batch_execute",
            {
                "commands": [
                    {"label": "a", "command": "gh pr view 1"},
                    {"label": "b", "command": "python3 -m karte close-attempt --issue 1"},
                ]
            },
        )
        self.assertEqual(commands, ["gh pr view 1", "python3 -m karte close-attempt --issue 1"])

    def test_unsupported_tool_returns_empty(self):
        self.assertEqual(notify.extract_commands("Write", {"file_path": "x"}), [])

    def test_malformed_input_returns_empty(self):
        self.assertEqual(notify.extract_commands("Bash", {"command": 123}), [])
        self.assertEqual(
            notify.extract_commands(
                "mcp__plugin_context-mode_context-mode__ctx_batch_execute", {"commands": "nope"}
            ),
            [],
        )
        self.assertEqual(
            notify.extract_commands("mcp__plugin_context-mode_context-mode__ctx_execute", {"code": 1}),
            [],
        )


class NotificationContentTests(unittest.TestCase):
    """Issue #512 是正（F-512-03）: escalate 根拠と verdict 内訳が本文に現れることを固定する。"""

    def test_escalate_body_includes_stalled_and_saturated(self):
        current = {
            "issue": 512,
            "verdict": "harmful-open",
            "escalate": True,
            "blocking_findings": ["F-512-01"],
            "blocking_harmful": ["F-512-01"],
            "undecided_disposition": ["F-512-01"],
            "stalled_findings": ["F-431-07"],
            "saturated_groups": [["3", "5"]],
            "findings": [finding("F-512-01", "open")],
        }
        message, _ = notify.decide(current, previous=None)
        assert message is not None
        self.assertIn("F-431-07", message)
        self.assertIn("飽和したアプローチ", message)
        self.assertIn("3, 5", message)
        self.assertIn("clean を妨げる実害あり", message)
        self.assertIn("実害あり・disposition 未決定", message)

    def test_non_escalate_body_omits_stalled_and_saturated_labels(self):
        current = {
            "issue": 512,
            "verdict": "clean",
            "escalate": False,
            "blocking_findings": [],
            "blocking_harmful": [],
            "undecided_disposition": [],
            "stalled_findings": [],
            "saturated_groups": [],
            "findings": [],
        }
        message, _ = notify.decide(current, previous=None)
        assert message is not None
        self.assertNotIn("無進捗（stalled）", message)
        self.assertNotIn("飽和したアプローチ", message)


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

    def test_mixed_open_and_already_read_resolved_shows_only_open(self):
        # Issue #512 是正（F-512-05）: 他に open があって通知自体は出る場合でも、
        # 既読の resolved 分（F-512-02）は載らないことを固定する。
        current = payload(
            512,
            verdict="harmful-open",
            findings=[
                finding("F-512-01", "open"),
                finding("F-512-02", "resolved"),
            ],
        )
        previous = {
            "findings": {"F-512-01": "open", "F-512-02": "resolved"},
            "verdict": "harmful-open",
            "escalate": False,
        }
        message, snapshot = notify.decide(current, previous)
        assert message is not None
        self.assertIn("F-512-01", message)
        self.assertNotIn("F-512-02", message)
        self.assertEqual(snapshot["findings"]["F-512-02"], "resolved")


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

    def test_ctx_execute_triggers_notification(self):
        # Issue #512 是正（F-512-02）: ctx_execute 経由の ingest-review も検出する。
        status = payload(512, verdict="harmful-open", findings=[finding("F-512-01", "open")])
        code = self.invoke(
            {
                "tool_name": "mcp__plugin_context-mode_context-mode__ctx_execute",
                "tool_input": {
                    "language": "shell",
                    "code": "python3 -m karte ingest-review --issue 512 --round 1 --from -",
                },
            },
            self.runner_returning(status),
        )
        self.assertEqual(code, 0)
        decision = json.loads(self.stdout.getvalue())
        self.assertIn("F-512-01", decision["systemMessage"])

    def test_ctx_batch_execute_triggers_notification(self):
        # Issue #512 是正（F-512-02）: ctx_batch_execute の commands[] を全件検査する。
        status = payload(512, verdict="harmful-open", findings=[finding("F-512-01", "open")])
        code = self.invoke(
            {
                "tool_name": "mcp__plugin_context-mode_context-mode__ctx_batch_execute",
                "tool_input": {
                    "commands": [
                        {"label": "unrelated", "command": "gh pr view 526"},
                        {
                            "label": "close-attempt",
                            "command": "python3 -m karte close-attempt --issue 512 --outcome fixed",
                        },
                    ]
                },
            },
            self.runner_returning(status),
        )
        self.assertEqual(code, 0)
        decision = json.loads(self.stdout.getvalue())
        self.assertIn("F-512-01", decision["systemMessage"])

    def test_ctx_execute_file_is_not_supported(self):
        # ctx_execute_file は既存方針で全ロール未付与のため対象に含めない。
        code = self.invoke(
            {
                "tool_name": "mcp__plugin_context-mode_context-mode__ctx_execute_file",
                "tool_input": {
                    "path": "x.py",
                    "language": "python",
                    "code": "python3 -m karte close-attempt --issue 512",
                },
            },
            self.runner_returning({}),
        )
        self.assertEqual(code, 0)
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertEqual(self.runner_calls, [])

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
