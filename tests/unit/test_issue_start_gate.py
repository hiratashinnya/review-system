"""Issue #297 managed Issue-start adapter/hook tests（Issue #309 で台帳起票を追加）。"""

import io
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from blocker_gate.model import POLICY_VERSION
from issue_start import worktree_ledger
from issue_start.gate import (
    BINDING_MARKER,
    FIX_BINDING_MARKER,
    IsolationOnlyAck,
    IssueStartError,
    IssueStartRequest,
    _validate_tool_input_shape,
    evaluate_issue_start,
    parse_dispatch_payload,
    record_open_entry,
)
from issue_start.hook import run as run_hook


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parents[1] / "fixtures" / "blocker_gate"
OID = "a" * 40
LEDGER_NOW = datetime(2026, 8, 19, 4, 11, 7, tzinfo=timezone.utc)


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class Collector:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.waiver_calls = 0

    def collect_issue(self, repository, number):
        return self.snapshot

    def collect_waiver_materials(self, repository, refs):
        self.waiver_calls += 1
        raise AssertionError("#299前に waiver provider を呼んではならない")

    def issue_metadata(self, repository, number):
        return {
            "number": number,
            "title": f"blocker {number}",
            "html_url": f"https://github.com/{repository}/issues/{number}",
        }


def request(repository="example/repo", issue=10):
    return IssueStartRequest("issue-pipeline", repository, issue)


def claude_binding():
    return {
        "entrypoint": "issue-pipeline",
        "repository": "example/repo",
        "issue": 10,
        "branch_name": "issue-297",
        "base_ref": "main",
        "base_oid": OID,
        "base_pr": None,
    }


class FakeCompleted:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def git_runner(*, origin="https://github.com/example/repo.git", inside="true", top=ROOT):
    def run(argv, **kwargs):
        if argv == ["git", "rev-parse", "--is-inside-work-tree"]:
            return FakeCompleted(inside + "\n")
        if argv == ["git", "rev-parse", "--show-toplevel"]:
            return FakeCompleted(str(top) + "\n")
        if argv == ["git", "remote", "get-url", "origin"]:
            return FakeCompleted(origin + "\n")
        raise AssertionError(f"unexpected git argv: {argv}")
    return run


class DispatchPayloadMixin:
    """Codex/Claude の正規 dispatch payload を組み立てる共通ヘルパ（テストは持たない）。"""

    def codex_payload(self, *, task_name="issue_10", tool="collaborationspawn_agent", cwd=ROOT):
        return {
            "cwd": str(cwd),
            "tool_name": tool,
            "tool_input": {
                "agent_type": "issue-implementer",
                "fork_turns": "all",
                "task_name": task_name,
                # Codex 0.146.0 の実測では message は暗号化値。binding に使わない。
                "message": "ENC[AQICAH-encrypted-prompt]",
            },
        }

    def claude_payload(self, binding=None, *, tool="Task", isolation="worktree"):
        raw = claude_binding() if binding is None else binding
        tool_input = {
            "subagent_type": "issue-implementer",
            "prompt": BINDING_MARKER + json.dumps(raw, separators=(",", ":")),
            "description": "hook deny probe",
        }
        # Issue #350: 正規の dispatch は必ず `isolation: "worktree"` を伴う。
        if isolation is not None:
            tool_input["isolation"] = isolation
        return {"tool_name": tool, "tool_input": tool_input}


class DispatchPayloadTests(DispatchPayloadMixin, unittest.TestCase):
    def test_codex_encrypted_message_uses_task_name_and_worktree_origin(self):
        for tool_name in ("spawn_agent", "collaborationspawn_agent"):
            with self.subTest(tool_name=tool_name):
                actual = parse_dispatch_payload(
                    self.codex_payload(tool=tool_name), cwd=ROOT, runner=git_runner()
                )
                self.assertEqual(actual, request())

    def test_codex_accepts_strict_github_https_and_ssh_origins(self):
        for origin in (
            "https://github.com/example/repo.git",
            "git@github.com:example/repo.git",
            "ssh://git@github.com/example/repo.git",
        ):
            with self.subTest(origin=origin):
                actual = parse_dispatch_payload(
                    self.codex_payload(), cwd=ROOT, runner=git_runner(origin=origin)
                )
                self.assertEqual(actual.repository, "example/repo")

    def test_codex_bad_or_missing_task_name_is_fail_close(self):
        for task_name in (None, "", "issue_0", "issue_01", "issue-10", "issue_10_more", "xissue_10"):
            payload = self.codex_payload()
            if task_name is None:
                del payload["tool_input"]["task_name"]
            else:
                payload["tool_input"]["task_name"] = task_name
            with self.subTest(task_name=task_name), self.assertRaisesRegex(
                IssueStartError,
                "ISSUE_START_(TOOL_INPUT_SHAPE_INVALID|TASK_NAME_INVALID)",
            ):
                parse_dispatch_payload(payload, cwd=ROOT, runner=git_runner())

    def test_codex_bad_cwd_worktree_and_origin_are_fail_close(self):
        cases = [
            (self.codex_payload(cwd=ROOT.parent), git_runner(), "ISSUE_START_CWD_MISMATCH"),
            (self.codex_payload(), git_runner(inside="false"), "ISSUE_START_NOT_WORKTREE"),
            (self.codex_payload(), git_runner(top=ROOT.parent), "ISSUE_START_WORKTREE_ROOT_MISMATCH"),
            (self.codex_payload(), git_runner(origin="https://evil.example/example/repo.git"), "ISSUE_START_ORIGIN_INVALID"),
            (self.codex_payload(), git_runner(origin="http://github.com/example/repo.git"), "ISSUE_START_ORIGIN_INVALID"),
            (self.codex_payload(), git_runner(origin="https://user@github.com/example/repo.git"), "ISSUE_START_ORIGIN_INVALID"),
        ]
        for payload, runner, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(IssueStartError, reason):
                parse_dispatch_payload(payload, cwd=ROOT, runner=runner)

    def test_claude_task_and_runtime_agent_alias_use_marker_contract(self):
        for tool_name in ("Task", "Agent"):
            with self.subTest(tool_name=tool_name):
                self.assertEqual(
                    parse_dispatch_payload(self.claude_payload(tool=tool_name)), request()
                )
        bad = claude_binding()
        bad.pop("base_oid")
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_UNKNOWN_FIELD"):
            parse_dispatch_payload(self.claude_payload(bad))
        wrong_entrypoint = claude_binding()
        wrong_entrypoint["entrypoint"] = "other-pipeline"
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_ENTRYPOINT_UNKNOWN"):
            parse_dispatch_payload(self.claude_payload(wrong_entrypoint))

    def test_codex_agent_matcher_alias_is_not_a_codex_payload_alias(self):
        with self.assertRaisesRegex(
            IssueStartError, "ISSUE_START_TOOL_INPUT_SHAPE_INVALID"
        ):
            parse_dispatch_payload(
                self.codex_payload(tool="Agent"), cwd=ROOT, runner=git_runner()
            )

    def test_claude_shape_rejects_codex_field_mixing(self):
        for field, value in (
            ("agent_type", "issue-implementer"),
            ("message", "ENC[AQICAH-encrypted-prompt]"),
            ("task_name", "issue_10"),
        ):
            payload = self.claude_payload(tool="Agent")
            payload["tool_input"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_(TARGET_UNKNOWN|TOOL_INPUT_SHAPE_INVALID)"
            ):
                parse_dispatch_payload(payload)

    def test_unknown_or_similar_tool_names_are_not_payload_aliases(self):
        for tool_name in (
            "collaboration.spawn_agent",
            "evil.spawn_agent",
            "evilspawn_agent",
            "collaborationspawn_agent_extra",
            "collaborationspawn_agents",
        ):
            with self.subTest(tool_name=tool_name), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ENTRYPOINT_UNKNOWN"
            ):
                parse_dispatch_payload(
                    self.codex_payload(tool=tool_name), cwd=ROOT, runner=git_runner()
                )
        for tool_name in ("agent", "Agents", "TaskAgent", "Agent_extra"):
            with self.subTest(tool_name=tool_name), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ENTRYPOINT_UNKNOWN"
            ):
                parse_dispatch_payload(self.claude_payload(tool=tool_name))

    def test_non_issue_agent_is_explicitly_unmanaged(self):
        payload = self.codex_payload()
        payload["tool_input"]["agent_type"] = "explorer"
        self.assertIsNone(parse_dispatch_payload(payload, cwd=ROOT, runner=git_runner()))

    def test_missing_or_ambiguous_target_is_fail_close(self):
        missing = self.codex_payload()
        del missing["tool_input"]["agent_type"]
        ambiguous = self.codex_payload()
        ambiguous["tool_input"]["subagent_type"] = "issue-implementer"
        for payload in (missing, ambiguous):
            with self.assertRaisesRegex(IssueStartError, "ISSUE_START_TARGET_UNKNOWN"):
                parse_dispatch_payload(payload, cwd=ROOT, runner=git_runner())


class IsolationContractTests(DispatchPayloadMixin, unittest.TestCase):
    """Issue #350: Claude dispatch は `isolation: "worktree"` を欠くと deny される。

    分離は role 側では実現できない（gitgate に worktree を作成・移動する verb が無く、
    agent-command-gate の
    層2 が `cd` を deny する）ので、dispatch 側の指定だけが「isolated worktree」契約を
    成立させる唯一の手段。欠落は fail-close で拒否する。
    """

    def test_claude_dispatch_with_worktree_isolation_is_bound(self):
        payload = self.claude_payload()
        self.assertEqual(payload["tool_input"]["isolation"], "worktree")
        for tool_name in ("Task", "Agent"):
            with self.subTest(tool_name=tool_name):
                self.assertEqual(
                    parse_dispatch_payload(self.claude_payload(tool=tool_name)), request()
                )

    def test_claude_dispatch_without_worktree_isolation_is_denied(self):
        # None＝field 自体が無い（isolation を渡し忘れた dispatch）。
        for isolation in (None, "remote", "", "Worktree", "worktree ", 1, True, ["worktree"]):
            with self.subTest(isolation=isolation), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ISOLATION_NOT_WORKTREE"
            ):
                parse_dispatch_payload(self.claude_payload(isolation=isolation))

    def test_isolation_check_does_not_mask_more_fundamental_shape_errors(self):
        # required field 欠落は isolation より先に報告する（直す順序を誤らせない）。
        payload = self.claude_payload(isolation=None)
        del payload["tool_input"]["prompt"]
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_TOOL_INPUT_SHAPE_INVALID"):
            parse_dispatch_payload(payload)

    def test_codex_transport_carries_no_isolation_requirement(self):
        # Codex の spawn_agent に isolation パラメータは無い。claude 側の要求を持ち込まない。
        self.assertEqual(
            parse_dispatch_payload(self.codex_payload(), cwd=ROOT, runner=git_runner()),
            request(),
        )

    def test_unmanaged_agents_are_never_required_to_declare_isolation(self):
        # unmanaged な dispatch を巻き込むと全委譲が壊れる。素通し（None）を固定する。
        # **`issue-fixer` は Issue #354 PR-4 で `isolation_only` へ移ったのでここには入らない**
        # （IsolationOnlyContractTests が別途 deny 側を固定する）。
        for agent in ("pr-reviewer", "general-purpose", "dsv2-lookup"):
            payload = self.claude_payload(isolation=None)
            payload["tool_input"]["subagent_type"] = agent
            with self.subTest(agent=agent):
                self.assertIsNone(parse_dispatch_payload(payload))

    def test_broken_manifest_isolation_value_fails_close(self):
        # manifest 破損（非文字列・空）を「要求なし」と誤読して素通ししない。
        for broken in ("", None, 1, True, ["worktree"]):
            transport = {
                "required_tool_input_fields": ["subagent_type", "prompt"],
                "forbidden_tool_input_fields": ["agent_type"],
                "required_isolation": broken,
            }
            with self.subTest(broken=broken), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_MANIFEST_CONTRACT_ERROR"
            ):
                _validate_tool_input_shape(
                    {"subagent_type": "issue-implementer", "prompt": "x", "isolation": "worktree"},
                    transport,
                )


def fix_binding(**overrides):
    raw = {
        "issue": 354,
        "round": 1,
        "branch_name": "claude/issue-354-pr4",
        "repository": "example/repo",
        "expected_oid": "b" * 40,
        "handoff_path": "tmp/_handoff/issue-fixer--issue-354-fix1.yaml",
    }
    raw.update(overrides)
    return raw


def fixer_payload(binding=None, *, tool="Task", isolation="worktree", agent="issue-fixer"):
    raw = fix_binding() if binding is None else binding
    tool_input = {
        "subagent_type": agent,
        "prompt": "fix findings\n"
        + FIX_BINDING_MARKER
        + json.dumps(raw, separators=(",", ":")),
        "description": "remediation round",
    }
    if isolation is not None:
        tool_input["isolation"] = isolation
    return {"tool_name": tool, "tool_input": tool_input}


class IsolationOnlyContractTests(unittest.TestCase):
    """Issue #354 PR-4: `issue-fixer` は「分離だけを課す」区分として dispatch を検証される。

    managed（`issue-implementer`）との差は **GitHub API を叩かないこと**であって、
    shape / isolation / marker の厳しさではない。緩んでいないことをここで固定する。
    """

    def test_valid_fixer_dispatch_returns_an_isolation_only_ack(self):
        for tool_name in ("Task", "Agent"):
            with self.subTest(tool_name=tool_name):
                ack = parse_dispatch_payload(fixer_payload(tool=tool_name))
                self.assertEqual(
                    ack,
                    IsolationOnlyAck(
                        entrypoint="issue-pipeline",
                        agent_type="issue-fixer",
                        issue=354,
                        round=1,
                        branch_name="claude/issue-354-pr4",
                        handoff_path="tmp/_handoff/issue-fixer--issue-354-fix1.yaml",
                        expected_oid="b" * 40,
                        repository="example/repo",
                    ),
                )

    def test_missing_or_wrong_isolation_is_denied(self):
        for isolation in (None, "remote", "", "Worktree", "worktree ", 1, True, ["worktree"]):
            with self.subTest(isolation=isolation), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_ISOLATION_NOT_WORKTREE"
            ):
                parse_dispatch_payload(fixer_payload(isolation=isolation))

    def test_missing_or_duplicated_marker_is_fail_close(self):
        payload = fixer_payload()
        payload["tool_input"]["prompt"] = "fix findings without a marker"
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_MISSING_OR_DUPLICATE"):
            parse_dispatch_payload(payload)
        duplicated = fixer_payload()
        line = FIX_BINDING_MARKER + json.dumps(fix_binding(), separators=(",", ":"))
        duplicated["tool_input"]["prompt"] = line + "\n" + line
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_MISSING_OR_DUPLICATE"):
            parse_dispatch_payload(duplicated)

    def test_invalid_json_marker_is_fail_close(self):
        payload = fixer_payload()
        payload["tool_input"]["prompt"] = FIX_BINDING_MARKER + "{not json"
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_INVALID_JSON"):
            parse_dispatch_payload(payload)
        not_object = fixer_payload()
        not_object["tool_input"]["prompt"] = FIX_BINDING_MARKER + "[1,2]"
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_INVALID_JSON"):
            parse_dispatch_payload(not_object)

    def test_field_set_must_be_exact(self):
        extra = fix_binding()
        extra["base_pr"] = None
        missing = fix_binding()
        del missing["expected_oid"]
        missing_repository = fix_binding()
        del missing_repository["repository"]
        for raw in (extra, missing, missing_repository):
            with self.subTest(raw=sorted(raw)), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_BINDING_UNKNOWN_FIELD"
            ):
                parse_dispatch_payload(fixer_payload(raw))

    def test_field_values_are_validated(self):
        cases = [
            ({"issue": 0}, "ISSUE_START_ISSUE_INVALID"),
            ({"issue": "354"}, "ISSUE_START_ISSUE_INVALID"),
            ({"issue": True}, "ISSUE_START_ISSUE_INVALID"),
            ({"round": 0}, "ISSUE_START_ROUND_INVALID"),
            ({"round": None}, "ISSUE_START_ROUND_INVALID"),
            ({"round": "1"}, "ISSUE_START_ROUND_INVALID"),
            ({"branch_name": "-evil"}, "ISSUE_START_BRANCH_INVALID"),
            ({"branch_name": ""}, "ISSUE_START_BRANCH_INVALID"),
            ({"repository": ""}, "ISSUE_START_REPOSITORY_INVALID"),
            ({"repository": "no-slash"}, "ISSUE_START_REPOSITORY_INVALID"),
            ({"repository": "owner/repo/extra"}, "ISSUE_START_REPOSITORY_INVALID"),
            ({"repository": None}, "ISSUE_START_REPOSITORY_INVALID"),
            ({"expected_oid": "b" * 39}, "ISSUE_START_EXPECTED_OID_INVALID"),
            ({"expected_oid": "B" * 40}, "ISSUE_START_EXPECTED_OID_INVALID"),
            ({"expected_oid": None}, "ISSUE_START_EXPECTED_OID_INVALID"),
        ]
        for override, reason in cases:
            with self.subTest(override=override), self.assertRaisesRegex(IssueStartError, reason):
                parse_dispatch_payload(fixer_payload(fix_binding(**override)))

    def test_handoff_path_must_be_relative_and_bound_to_the_issue(self):
        bad_paths = [
            "/abs/tmp/_handoff/issue-fixer--issue-354.yaml",
            "tmp/_handoff/../../etc/issue-fixer--issue-354.yaml",
            "tmp/_handoff/sub/issue-fixer--issue-354.yaml",
            "tmp/_karte/issue-fixer--issue-354.yaml",
            "tmp/_handoff/issue-fixer--issue-354.txt",
            # 境界検査: 別 Issue のファイル（`issue-3541`）を受理しない。
            "tmp/_handoff/issue-fixer--issue-3541.yaml",
            # agent_type 束縛: implementer 側のハンドオフを上書きさせない。
            "tmp/_handoff/issue-implementer--issue-354.yaml",
            "",
        ]
        for path in bad_paths:
            with self.subTest(path=path), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_HANDOFF_PATH_INVALID"
            ):
                parse_dispatch_payload(fixer_payload(fix_binding(handoff_path=path)))
        # サフィックス無し・`.` 区切りはどちらも受理する（ラウンド採番は呼び出し元の裁量）。
        for path in (
            "tmp/_handoff/issue-fixer--issue-354.yaml",
            "tmp/_handoff/issue-fixer--issue-354-fix2.yaml",
        ):
            with self.subTest(path=path):
                ack = parse_dispatch_payload(fixer_payload(fix_binding(handoff_path=path)))
                self.assertEqual(ack.handoff_path, path)

    def test_shape_errors_are_reported_before_the_marker_is_read(self):
        payload = fixer_payload(isolation=None)
        del payload["tool_input"]["prompt"]
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_TOOL_INPUT_SHAPE_INVALID"):
            parse_dispatch_payload(payload)

    def test_codex_field_mixing_is_rejected(self):
        for field, value in (
            ("agent_type", "issue-fixer"),
            ("message", "ENC[AQICAH-encrypted-prompt]"),
            ("task_name", "issue_354"),
        ):
            payload = fixer_payload()
            payload["tool_input"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_(TARGET_UNKNOWN|TOOL_INPUT_SHAPE_INVALID)"
            ):
                parse_dispatch_payload(payload)

    def test_managed_dispatch_behaviour_is_unchanged(self):
        """回帰: `isolation_only` の追加が managed 経路（`issue-implementer`）を変えていない。"""
        payload = {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "dispatch",
                "isolation": "worktree",
            },
        }
        self.assertEqual(parse_dispatch_payload(payload), request())
        # `issue-implementer` の marker を `issue-fixer` に流用しても通らない（契約が別）。
        borrowed = fixer_payload()
        borrowed["tool_input"]["prompt"] = BINDING_MARKER + json.dumps(
            claude_binding(), separators=(",", ":")
        )
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BINDING_MISSING_OR_DUPLICATE"):
            parse_dispatch_payload(borrowed)

    def test_manifest_schema_version_mismatch_is_fail_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(
                json.dumps({
                    "schema_version": "managed-issue-entrypoints/1",
                    "policy_version": "issue-start/1.0",
                    "managed": [],
                }),
                encoding="utf-8",
            )
            with patch("issue_start.gate.ENTRYPOINT_MANIFEST", path), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_MANIFEST_CONTRACT_ERROR"
            ):
                parse_dispatch_payload(fixer_payload())

    def test_an_agent_type_in_both_sections_is_fail_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            entry = {
                "entrypoint": "issue-pipeline",
                "agent_type": "issue-fixer",
                "binding_transports": {
                    "claude": {
                        "tool_names": ["Task"],
                        "agent_type_field": "subagent_type",
                        "required_tool_input_fields": ["subagent_type", "prompt"],
                        "forbidden_tool_input_fields": ["agent_type"],
                        "prompt_field": "prompt",
                        "binding_marker": "ISSUE_FIX_BINDING_V1=",
                        "required_isolation": "worktree",
                    }
                },
            }
            path.write_text(
                json.dumps({
                    "schema_version": "managed-issue-entrypoints/2",
                    "policy_version": "issue-start/1.0",
                    "managed": [entry],
                    "isolation_only": [entry],
                }),
                encoding="utf-8",
            )
            with patch("issue_start.gate.ENTRYPOINT_MANIFEST", path), self.assertRaisesRegex(
                IssueStartError, "ISSUE_START_MANIFEST_CONTRACT_ERROR"
            ):
                parse_dispatch_payload(fixer_payload())


class EvaluationTests(unittest.TestCase):
    def test_allow_contains_blocker_evidence_only(self):
        collector = Collector(load("closed_direct.json"))
        result = evaluate_issue_start(request(), collector_factory=lambda token: collector)
        self.assertEqual((result["result"], result["exit_code"]), ("ALLOW", 0))
        self.assertEqual(result["reason"], "ISSUE_START_ALLOWED")
        self.assertNotIn("branch_source_evidence", result)
        self.assertEqual(collector.waiver_calls, 0)

    def test_block_and_collection_error_preserve_verdict(self):
        for fixture, verdict in [("open_direct.json", "BLOCK"), ("cycle.json", "ERROR")]:
            result = evaluate_issue_start(
                request(), collector_factory=lambda token, f=fixture: Collector(load(f))
            )
            self.assertEqual(result["result"], verdict)
            self.assertNotIn("branch_source_evidence", result)

    def test_block_report_has_number_title_url_path_and_next_action(self):
        result = evaluate_issue_start(
            request(), collector_factory=lambda token: Collector(load("open_direct.json"))
        )
        item = result["blockers"][0]
        self.assertEqual(item["number"], 9)
        self.assertEqual(item["title"], "blocker 9")
        self.assertIn("/issues/9", item["url"])
        self.assertEqual(item["path"], ["example/repo#10", "example/repo#9"])
        self.assertIn("fresh invocation", item["next_action"])

    def test_repository_issue_binding_mismatch_is_error(self):
        bad = load("closed_direct.json")
        bad["subject"]["number"] = 11
        with self.assertRaisesRegex(IssueStartError, "ISSUE_START_BLOCKER_BINDING_MISMATCH"):
            evaluate_issue_start(request(), collector_factory=lambda token: Collector(bad))


class HookLedgerMixin:
    """hook 経路の共通 fixture（テストは持たない）。"""

    def setUp(self):
        # Issue #309: ALLOW 経路は worktree 所有台帳へ `open` 起票する。実リポジトリの
        # `tmp/_worktree/` を汚さないよう、台帳の置き場をテストごとに隔離する。
        self._ledger_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._ledger_tmp.cleanup)
        self.ledger_root = Path(self._ledger_tmp.name).resolve()

    def ledger_entries(self):
        return worktree_ledger.read_ledger(self.ledger_root)["entries"]

    def managed_payload(self, task_name="issue_10"):
        return {
            "cwd": str(ROOT),
            "tool_name": "collaborationspawn_agent",
            "tool_input": {
                "agent_type": "issue-implementer",
                "task_name": task_name,
                "message": "ENC[AQICAH-encrypted-prompt]",
            },
        }


class HookTests(HookLedgerMixin, unittest.TestCase):
    def test_malformed_managed_dispatch_emits_deny(self):
        stdout = io.StringIO()
        rc = run_hook(
            stdin=io.StringIO(json.dumps(self.managed_payload("issue-10"))),
            stdout=stdout,
            stderr=io.StringIO(),
            cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
        )
        self.assertEqual(rc, 0)
        output = json.loads(stdout.getvalue())
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_codex_encrypted_message_allow_reaches_evaluation(self):
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch(
            "issue_start.hook.resolve_github_token", return_value="credential-from-gh"
        ), patch("issue_start.hook.evaluate_issue_start", return_value=evidence) as evaluate:
            run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload())),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())
        self.assertEqual(evaluate.call_args.args[0].issue, 10)
        self.assertEqual(evaluate.call_args.args[0].repository, "hiratashinnya/review-system")
        self.assertEqual(evaluate.call_args.kwargs["token"], "credential-from-gh")

    def test_issue_317_equivalent_allows_with_mocked_gh_credential(self):
        repository = "hiratashinnya/review-system"
        snapshot = {
            "schema": "blocker-gate-snapshot/v1",
            "policy_version": POLICY_VERSION,
            "mode": "issue-start",
            "repository": repository,
            "subject": {"type": "issue", "number": 317},
            "roots": [f"{repository}#317"],
            "virtual_closed": [],
            "nodes": {
                f"{repository}#317": {
                    "node_id": "I317",
                    "state": "OPEN",
                    "blocked_by": [f"{repository}#316"],
                    "parent": None,
                    "children": [],
                },
                f"{repository}#316": {
                    "node_id": "I316",
                    "state": "CLOSED_COMPLETED",
                    "blocked_by": [],
                    "parent": None,
                    "children": [],
                },
            },
            "pages_complete": True,
            "errors": [],
            "fetched_at": "2026-08-09T00:00:00Z",
            "graphql_closing_set": [],
            "delivered_message_closing_set": [],
            "binding": {},
        }
        secret = "credential-from-mocked-gh"

        def evaluate(request, *, token, cwd=None):
            self.assertEqual(token, secret)
            return evaluate_issue_start(
                request,
                token=token,
                cwd=cwd,
                collector_factory=lambda actual: Collector(snapshot),
            )

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=secret), patch(
            "issue_start.hook.evaluate_issue_start", side_effect=evaluate
        ):
            rc = run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload("issue_317"))),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

    def test_claude_runtime_agent_alias_allow_reaches_evaluation(self):
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
        }
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER
                + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "hook deny probe",
                "isolation": "worktree",
            },
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=evidence
        ) as evaluate:
            run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ISSUE_START_ALLOWED", stderr.getvalue())
        self.assertEqual(evaluate.call_args.args[0], request())

    def test_missing_isolation_denies_before_any_github_evaluation(self):
        """Issue #350 AC4: `isolation` 欠落を hook が機械的に deny し、直し方を deny 文に載せる。"""
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER
                + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "hook deny probe",
            },
        }
        stdout = io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start"
        ) as evaluate:
            rc = run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(rc, 0)
        decision = json.loads(stdout.getvalue())["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        reason = decision["permissionDecisionReason"]
        self.assertIn("ISSUE_START_ISOLATION_NOT_WORKTREE", reason)
        # 「isolation を worktree にせよ」が deny 文だけで読み取れること（reason code だけにしない）。
        self.assertIn("isolation=worktree", reason)
        self.assertIn("actual=None", reason)
        # blocker 判定（GitHub API）まで進まずに落ちる＝dispatch 前に閉じる。
        evaluate.assert_not_called()

    def test_block_deny_reason_preserves_actionable_blocker_report(self):
        blocker = {
            "number": 9,
            "repository": "example/repo",
            "title": "required blocker",
            "url": "https://github.com/example/repo/issues/9",
            "path": ["example/repo#10", "example/repo#9"],
            "next_action": "blockerをcloseしてfresh invocationで再試行する",
        }
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "BLOCK",
            "exit_code": 10,
            "reason": "OPEN_BLOCKER",
            "blockers": [blocker],
        }
        stdout = io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=evidence
        ):
            run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload())),
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        reason = json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecisionReason"]
        report = json.loads(reason.split(" blockers=", 1)[1])
        self.assertEqual(report, [blocker])


class WorktreeLedgerSideEffectTests(HookLedgerMixin, unittest.TestCase):
    """Issue #309 PR-1: ALLOW した dispatch を所有台帳へ `open` 起票する（**deny はしない**）。"""

    ALLOW_EVIDENCE = {
        "schema_version": "issue-start-evidence/1",
        "policy_version": "issue-start/1.0",
        "result": "ALLOW",
        "exit_code": 0,
        "reason": "ISSUE_START_ALLOWED",
    }

    def claude_payload(self):
        return {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "dispatch",
                "isolation": "worktree",
            },
        }

    def run_allow(self, payload, *, ledger_root=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=dict(self.ALLOW_EVIDENCE)
        ):
            rc = run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
                ledger_root=self.ledger_root if ledger_root is None else ledger_root,
                now=LEDGER_NOW,
            )
        return rc, stdout, stderr

    def test_allow_opens_a_ledger_entry_bound_to_the_dispatch(self):
        rc, stdout, stderr = self.run_allow(self.claude_payload())
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "", "起票は dispatch を deny しない")
        entries = self.ledger_entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["issue"], 10)
        self.assertEqual(entry["agent_type"], "issue-implementer")
        self.assertEqual(entry["branch_name"], "issue-297")
        self.assertEqual(entry["status"], "open")
        self.assertEqual(entry["dispatched_at"], "2026-08-19T04:11:07Z")
        # marker v1 に無い項目は推測せず None のまま（marker 拡張は後続 PR）。
        self.assertIsNone(entry["round"])
        self.assertIsNone(entry["handoff_path"])
        self.assertIsNone(entry["agent_id"])
        self.assertIsNone(entry["worktree_path"])
        # evidence（stderr）に entry_id が載る。
        evidence = json.loads(stderr.getvalue())
        self.assertEqual(evidence["ledger"]["entry_id"], entry["entry_id"])
        self.assertIsNone(evidence["ledger"]["error"])

    def test_codex_dispatch_without_a_marker_records_no_branch_name(self):
        rc, _stdout, _stderr = self.run_allow(self.managed_payload())
        self.assertEqual(rc, 0)
        entry = self.ledger_entries()[0]
        self.assertEqual(entry["agent_type"], "issue-implementer")
        self.assertIsNone(entry["branch_name"], "Codex transport に branch_name は無い")

    def test_broken_ledger_now_denies_fail_close(self):
        """Issue #354 PR-3 で **fail-open → fail-close** へ倒した箇所（契約変更の明示）。

        PR-1（#309）では台帳が壊れていても ALLOW のままだった——観測が正確になったことを
        実測してから deny を有効化する「統制を先に、付与は別 PR」の順序を守るため。
        PR-3 は残留 worktree を deny の材料にするので、**台帳を一意に読めない間は
        残留の有無を判定できない**＝通してはならない。

        起票（`record_open_entry`）そのものは今も fail-open で、
        :meth:`test_record_open_entry_never_raises` がその不変条件を保っている。
        """
        broken = self.ledger_root / "broken"
        broken.mkdir()
        path = worktree_ledger.ledger_path(broken, create_dir=True)
        path.write_text("{not json", encoding="utf-8")
        rc, stdout, _stderr = self.run_allow(self.claude_payload(), ledger_root=broken)
        self.assertEqual(rc, 0)
        decision = json.loads(stdout.getvalue())["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        reason = decision["permissionDecisionReason"]
        self.assertIn("ISSUE_START_WORKTREE_LEDGER_ERROR", reason)
        self.assertIn("LEDGER_INVALID_JSON", reason)
        self.assertIn("fail-close", reason)

    def test_allow_evidence_carries_the_worktree_residue_report(self):
        """FR-W12: 解放の実施/未実施が台帳と突き合わせられる形で evidence に残る。"""
        _rc, _stdout, stderr = self.run_allow(self.claude_payload())
        residue = json.loads(stderr.getvalue())["worktree_residue"]
        self.assertEqual(residue["stale"], [])
        self.assertEqual(residue["unclaimed"], [])
        self.assertEqual(residue["swept"], [])
        self.assertIn("claimed", residue)

    def test_denied_dispatch_records_nothing(self):
        stdout = io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None):
            rc = run_hook(
                stdin=io.StringIO(json.dumps(self.managed_payload("issue-10"))),
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(
            json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecision"], "deny"
        )
        self.assertEqual(self.ledger_entries(), [], "deny した dispatch は起票しない")

    def test_record_open_entry_never_raises(self):
        """gate の起票関数は**どんな入力でも例外を投げない**（fail-open の実体）。"""
        for label, payload in (
            ("empty", {}),
            ("no-tool-input", {"tool_name": "Task"}),
            ("tool-input-not-a-mapping", {"tool_name": "Task", "tool_input": "x"}),
            ("no-agent-type", {"tool_name": "Task", "tool_input": {"prompt": "x"}}),
        ):
            with self.subTest(label=label):
                result = record_open_entry(
                    payload, request(), now=LEDGER_NOW, repo_root=self.ledger_root
                )
                self.assertIsNone(result["entry_id"])
                self.assertEqual(result["error"], "LEDGER_AGENT_TYPE_UNREADABLE")
        self.assertEqual(self.ledger_entries(), [])

    def test_record_open_entry_converges_on_the_main_worktree(self):
        """linked worktree から起動しても台帳は main worktree 側に1つだけ作られる。"""
        main = self.ledger_root / "main"
        gitdir = main / ".git" / "worktrees" / "agent-abc"
        gitdir.mkdir(parents=True)
        (gitdir / "commondir").write_text("../..\n", encoding="utf-8")
        linked = main / ".claude" / "worktrees" / "agent-abc"
        linked.mkdir(parents=True)
        (linked / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")

        result = record_open_entry(
            self.claude_payload(), request(), now=LEDGER_NOW, repo_root=linked
        )
        self.assertIsNotNone(result["entry_id"])
        self.assertTrue((main / "tmp" / "_worktree" / "ledger.json").is_file())
        self.assertFalse((linked / "tmp").exists())


class IsolationOnlyHookTests(HookLedgerMixin, unittest.TestCase):
    """Issue #354 PR-4: hook 経路での `isolation_only`（`issue-fixer`）の挙動。"""

    def run_dispatch(self, payload):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start"
        ) as evaluate:
            rc = run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout,
                stderr=stderr,
                cwd=ROOT,
                ledger_root=self.ledger_root,
                now=LEDGER_NOW,
            )
        self.assertEqual(rc, 0)
        return stdout.getvalue(), stderr.getvalue(), evaluate

    def test_allowed_without_touching_the_blocker_gate(self):
        stdout, stderr, evaluate = self.run_dispatch(fixer_payload())
        self.assertEqual(stdout, "", "分離だけを課す区分は deny しない")
        # 是正ラウンドは GitHub API を叩かない（API 不通でレビュー是正まで止めないため）。
        evaluate.assert_not_called()
        evidence = json.loads(stderr)
        self.assertEqual(evidence["result"], "ISOLATION_ONLY")
        self.assertEqual(evidence["reason"], "ISSUE_START_ISOLATION_ONLY_ALLOWED")
        self.assertIsNone(evidence["blocker_evidence"])
        self.assertEqual(evidence["binding"]["agent_type"], "issue-fixer")
        self.assertEqual(evidence["binding"]["round"], 1)
        self.assertIn("claimed", evidence["worktree_residue"])

    def test_the_ledger_entry_carries_issue_round_branch_and_handoff_path(self):
        """FR-W4 完全化: marker の値を推測せずそのまま台帳へ載せる。"""
        _stdout, stderr, _evaluate = self.run_dispatch(fixer_payload())
        entries = self.ledger_entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["issue"], 354)
        self.assertEqual(entry["agent_type"], "issue-fixer")
        self.assertEqual(entry["round"], 1)
        self.assertEqual(entry["branch_name"], "claude/issue-354-pr4")
        self.assertEqual(entry["handoff_path"], "tmp/_handoff/issue-fixer--issue-354-fix1.yaml")
        self.assertEqual(entry["status"], "open")
        self.assertEqual(json.loads(stderr)["ledger"]["entry_id"], entry["entry_id"])

    def test_denied_dispatch_records_nothing_and_never_evaluates(self):
        stdout, _stderr, evaluate = self.run_dispatch(fixer_payload(isolation=None))
        decision = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        reason = decision["permissionDecisionReason"]
        self.assertIn("ISSUE_START_ISOLATION_NOT_WORKTREE", reason)
        self.assertIn("isolation=worktree", reason)
        evaluate.assert_not_called()
        self.assertEqual(self.ledger_entries(), [], "deny した dispatch は起票しない")


class WorktreeResidueDenyTests(HookLedgerMixin, unittest.TestCase):
    """Issue #354 PR-3（候補C）: 残留 worktree のある状態での次 dispatch を deny する。

    #354 が実測した事象は「残留 worktree があるのに `pr-reviewer` を dispatch し、
    レビューアが古い作業ツリーを掴んだ」——つまり **unmanaged 側**で起きた。したがって
    この deny は managed dispatch に限らず**全 `Task` dispatch** に掛かる。
    """

    def bind(self, agent_id, *, agent_type="issue-implementer", issue=354):
        worktree_ledger.open_entry(
            self.ledger_root, issue=issue, agent_type=agent_type, round=None,
            branch_name=None, handoff_path=None, now=LEDGER_NOW,
        )
        return worktree_ledger.bind_agent(
            self.ledger_root, agent_type=agent_type, agent_id=agent_id,
            worktree_path=f".claude/worktrees/agent-{agent_id}",
        )

    def make_worktree(self, name):
        path = self.ledger_root / ".claude" / "worktrees" / name
        path.mkdir(parents=True)
        return path

    def advance(self, entry_id, *statuses):
        for status in statuses:
            worktree_ledger.mark(self.ledger_root, entry_id, status, now=LEDGER_NOW)

    def managed_dispatch(self):
        return {
            "tool_name": "Task",
            "tool_input": {
                "subagent_type": "issue-implementer",
                "prompt": BINDING_MARKER + json.dumps(claude_binding(), separators=(",", ":")),
                "description": "dispatch",
                "isolation": "worktree",
            },
        }

    def unmanaged_dispatch(self):
        """manifest に載っていない agent_type（`parse_dispatch_payload` は `None` を返す）。"""
        return {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "pr-reviewer", "prompt": "review PR #401"},
        }

    def run_dispatch(self, payload):
        stdout, stderr = io.StringIO(), io.StringIO()
        allow = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
        }
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=dict(allow)
        ) as evaluate:
            rc = run_hook(
                stdin=io.StringIO(json.dumps(payload)),
                stdout=stdout, stderr=stderr,
                cwd=ROOT, ledger_root=self.ledger_root, now=LEDGER_NOW,
            )
        self.assertEqual(rc, 0)
        return stdout.getvalue(), stderr.getvalue(), evaluate

    def deny_reason(self, payload):
        stdout, _stderr, evaluate = self.run_dispatch(payload)
        decision = json.loads(stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        # 残留判定は GitHub API より前（ローカルの状態だけで決まる）。
        evaluate.assert_not_called()
        return decision["permissionDecisionReason"]

    def test_uncollected_residue_denies_with_the_remediation_command(self):
        """`stale` / `stopped` / `collected` はいずれも「回収が完了していない」＝deny。"""
        cases = {
            "stale": ("stale",),
            "stopped": ("stopped",),
            "collected": ("stopped", "collected"),
        }
        for label, statuses in cases.items():
            with self.subTest(status=label):
                self.setUp()
                self.make_worktree("agent-left")
                entry_id = self.bind("left")
                self.advance(entry_id, *statuses)
                reason = self.deny_reason(self.managed_dispatch())
                self.assertIn("ISSUE_START_WORKTREE_RESIDUE", reason)
                # entry_id / status / worktree_path が deny 文だけで読み取れること。
                self.assertIn(entry_id, reason)
                self.assertIn(label, reason)
                self.assertIn(".claude/worktrees/agent-left", reason)
                # 解消コマンドを必ず載せる（過剰 deny の緩和はここで行う）。
                self.assertIn(
                    "python3 -m gitgate collect-worktree --entry <entry-id>", reason
                )
                self.assertIn("worktree-forget", reason, "逃げ道も併記する")

    def test_worktree_not_in_the_ledger_denies_as_unclaimed(self):
        self.make_worktree("agent-nobody")
        reason = self.deny_reason(self.managed_dispatch())
        self.assertIn("ISSUE_START_WORKTREE_UNCLAIMED", reason)
        self.assertIn(".claude/worktrees/agent-nobody", reason)
        self.assertIn("worktree-release", reason)
        self.assertIn("--force-uncollected", reason)

    def test_broken_ledger_denies_fail_close(self):
        path = worktree_ledger.ledger_path(self.ledger_root, create_dir=True)
        path.write_text("{not json", encoding="utf-8")
        reason = self.deny_reason(self.managed_dispatch())
        self.assertIn("ISSUE_START_WORKTREE_LEDGER_ERROR", reason)
        self.assertIn("LEDGER_INVALID_JSON", reason)

    def test_a_live_running_dispatch_is_not_denied(self):
        """`running`＝live な dispatch が正当に占有している。deny しない。"""
        self.make_worktree("agent-live")
        self.bind("live")
        stdout, stderr, evaluate = self.run_dispatch(self.managed_dispatch())
        self.assertEqual(stdout, "", "live な worktree は残留ではない")
        evaluate.assert_called_once()
        residue = json.loads(stderr)["worktree_residue"]
        self.assertEqual(residue["running"], [".claude/worktrees/agent-live"])
        self.assertEqual(residue["unclaimed"], [])

    def test_stopped_is_claimed_for_unclaimed_but_still_a_residue(self):
        """`stopped` の二重の性質の境界（Issue #354 PR-3 の要注意点）。

        回収処理中の worktree を `ISSUE_START_WORKTREE_UNCLAIMED` として誤検出しては
        ならない（＝claimed 集合に含める）が、`stopped` のまま止まっている＝回収段が
        失敗している可能性があるので residue としては検出する。**deny の reason は
        UNCLAIMED ではなく RESIDUE になる**（解消コマンドが `collect-worktree` であって
        `worktree-release --force-uncollected` ではないから）。
        """
        self.make_worktree("agent-stopping")
        entry_id = self.bind("stopping")
        self.advance(entry_id, "stopped")
        reason = self.deny_reason(self.managed_dispatch())
        self.assertIn("ISSUE_START_WORKTREE_RESIDUE", reason)
        self.assertNotIn("ISSUE_START_WORKTREE_UNCLAIMED", reason)
        self.assertIn("collect-worktree", reason)

    def test_unmanaged_dispatch_is_denied_too(self):
        """#354 の実測事象（残留があるのに `pr-reviewer` を dispatch）を正面から塞ぐ。"""
        self.make_worktree("agent-left")
        entry_id = self.bind("left")
        self.advance(entry_id, "stale")
        reason = self.deny_reason(self.unmanaged_dispatch())
        self.assertIn("ISSUE_START_WORKTREE_RESIDUE", reason)

    def test_unmanaged_dispatch_without_residue_still_emits_evidence(self):
        """F-354-08: unmanaged の ALLOW でも stdout は無出力のまま、stderr に残留判定の
        evidence（swept / claimed / unclaimed を含む）が残る（従来は無出力だった）。"""
        stdout, stderr, evaluate = self.run_dispatch(self.unmanaged_dispatch())
        self.assertEqual(stdout, "", "unmanaged は素通し（deny しない）")
        evaluate.assert_not_called()
        evidence = json.loads(stderr)
        self.assertEqual(evidence["result"], "UNMANAGED")
        residue = evidence["worktree_residue"]
        self.assertEqual(residue["stale"], [])
        self.assertEqual(residue["unclaimed"], [])
        self.assertEqual(residue["swept"], [])
        self.assertIn("claimed", residue)

    def test_orphan_running_entry_is_swept_then_denied(self):
        """worktree が消えた `running` は掃引で `stale` に落ち、その場で deny される。

        放置すると `resolve_worktree_for_agent` が恒久的に `ambiguous-running` になり、
        以後どの dispatch も束縛できなくなる（PR-1 の既知の詰まり）。
        """
        entry_id = self.bind("vanished")  # ディスク上に worktree を作らない
        reason = self.deny_reason(self.managed_dispatch())
        self.assertIn("ISSUE_START_WORKTREE_RESIDUE", reason)
        self.assertIn(entry_id, reason)
        entries = worktree_ledger.read_ledger(self.ledger_root)["entries"]
        self.assertEqual(entries[0]["status"], "stale")

    def test_residue_deny_does_not_open_a_ledger_entry(self):
        self.make_worktree("agent-left")
        entry_id = self.bind("left")
        self.advance(entry_id, "stale")
        self.deny_reason(self.managed_dispatch())
        self.assertEqual(len(self.ledger_entries()), 1, "deny した dispatch は起票しない")

    def test_blocker_deny_evidence_shape_is_unchanged(self):
        """回帰: 既存 blocker gate 経路の deny 文（`blockers=` の JSON）が壊れていない。"""
        blocker = {
            "number": 9,
            "repository": "example/repo",
            "title": "required blocker",
            "url": "https://github.com/example/repo/issues/9",
            "path": ["example/repo#10", "example/repo#9"],
            "next_action": "blockerをcloseしてfresh invocationで再試行する",
        }
        evidence = {
            "schema_version": "issue-start-evidence/1",
            "policy_version": "issue-start/1.0",
            "result": "BLOCK",
            "exit_code": 10,
            "reason": "OPEN_BLOCKER",
            "blockers": [blocker],
        }
        stdout = io.StringIO()
        with patch("issue_start.hook.resolve_github_token", return_value=None), patch(
            "issue_start.hook.evaluate_issue_start", return_value=evidence
        ):
            run_hook(
                stdin=io.StringIO(json.dumps(self.managed_dispatch())),
                stdout=stdout, stderr=io.StringIO(),
                cwd=ROOT, ledger_root=self.ledger_root, now=LEDGER_NOW,
            )
        reason = json.loads(stdout.getvalue())["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("BLOCK OPEN_BLOCKER", reason)
        self.assertEqual(json.loads(reason.split(" blockers=", 1)[1]), [blocker])


if __name__ == "__main__":
    unittest.main()
