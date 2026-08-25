import io
import json
import re
import stat
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from pr_merge_gate.classifier import MergeOperation, PreUseClassification, classify_pre_use
from pr_merge_gate.hook import post_run, run


ROOT = Path(__file__).resolve().parents[2]


def operation() -> MergeOperation:
    return MergeOperation(
        repository="example/repo",
        pr_number=50,
        merge_method="squash",
        transport="connector",
        commit_title=None,
        commit_message=None,
        expected_head_oid=None,
        operation_fingerprint="sha256:" + "1" * 64,
    )


def allow_evidence() -> dict:
    return {
        "policy_version": "pr-merge-pre-use/1",
        "result": "ALLOW",
        "reason": "NO_VIOLATION",
        "binding": {
            "repository": "example/repo",
            "pr_number": 50,
            "merge_method": "squash",
            "transport": "connector",
            "operation_fingerprint": "sha256:" + "1" * 64,
            "head_oid": "a" * 40,
            "expected_commit_count": 1,
            "base_ref_name": "main",
            "default_branch": "main",
        },
        "graphql_closing_set": ["example/repo#7"],
        "delivered_message_closing_set": [],
        "closing_set": ["example/repo#7"],
        "findings": [
            {
                "code": "OPEN_BLOCKER",
                "subject": "example/repo#7",
                "path": ["example/repo#7", "example/repo#6"],
                "fingerprint": "sha256:" + "2" * 64,
                "waiver_id": "waiver-1",
            }
        ],
        "blocker_evidence": {"invocation_id": "inv-1"},
        "fetched_at": "2026-08-10T00:00:00Z",
        "permit_issued": True,
        "next_action": "invoke intercepted merge exactly once",
    }


class HookTest(unittest.TestCase):
    def invoke(self, payload: dict, audit_file: Path):
        payload = dict(payload)
        payload.setdefault("session_id", "session-1")
        payload.setdefault("turn_id", "turn-1")
        payload.setdefault("tool_use_id", "tool-1")
        payload.setdefault("hook_event_name", "PreToolUse")
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run(stdin=stdin, stdout=stdout, stderr=stderr, audit_file=audit_file)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_non_merge_operation_is_ignored_without_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            code, stdout, stderr = self.invoke(
                {"tool_name": "Bash", "tool_input": {"command": "gh issue view 50"}},
                target,
            )
            self.assertEqual((code, stdout, stderr), (0, "", ""))
            self.assertFalse(target.exists())

    def test_auto_merge_is_denied_and_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            code, stdout, stderr = self.invoke(
                {
                    "tool_name": "mcp__codex_apps__github_enable_auto_merge",
                    "tool_input": {"repository_full_name": "example/repo", "pr_number": 50},
                },
                target,
            )
            decision = json.loads(stdout)
            record = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertIn("AUTO_MERGE_DENIED", decision["hookSpecificOutput"]["permissionDecisionReason"])
            self.assertEqual(record["reason"], "AUTO_MERGE_DENIED")
            self.assertFalse(record["merge_api_called"])
            self.assertFalse(record["operation_dispatched"])
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_allow_is_audited_to_stderr_without_tool_result_mutation(self):
        merge = operation()
        classification = PreUseClassification(
            "merge", "CLASSIFIED", merge, merge.operation_fingerprint
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "pr_merge_gate.hook.classify_pre_use", return_value=classification
        ), patch(
            "pr_merge_gate.hook.resolve_github_token", return_value="token"
        ), patch(
            "pr_merge_gate.hook.evaluate_merge_operation", return_value=allow_evidence()
        ):
            target = Path(directory) / "audit.jsonl"
            code, stdout, stderr = self.invoke(
                {"tool_name": "mcp__codex_apps__github_merge_pull_request", "tool_input": {}},
                target,
            )
            self.assertEqual(code, 0)
            self.assertEqual(stdout, "")
            self.assertEqual(json.loads(stderr)["result"], "ALLOW")
            self.assertTrue(json.loads(target.read_text(encoding="utf-8"))["permit_issued"])

    def test_actions_free_pre_allow_call_and_post_response_are_correlated(self):
        payload = {
            "session_id": "session-e2e",
            "turn_id": "turn-e2e",
            "tool_use_id": "tool-e2e",
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__codex_apps__github_merge_pull_request",
            "tool_input": {
                "repository_full_name": "example/repo",
                "pr_number": 50,
                "merge_method": "squash",
            },
        }
        classified = __import__("pr_merge_gate.classifier", fromlist=["classify_pre_use"]).classify_pre_use(payload)
        permitted = allow_evidence()
        permitted["binding"]["operation_fingerprint"] = classified.operation.operation_fingerprint
        calls = []
        with tempfile.TemporaryDirectory() as directory, patch(
            "pr_merge_gate.hook.resolve_github_token", return_value="token"
        ), patch(
            "pr_merge_gate.hook.evaluate_merge_operation", return_value=permitted
        ):
            target = Path(directory) / "audit.jsonl"
            code, stdout, _ = self.invoke(payload, target)
            self.assertEqual((code, stdout), (0, ""))
            calls.append("managed merge invoked once")
            response = {"merged": True, "message": "secret-free result"}
            post_payload = dict(payload)
            post_payload["hook_event_name"] = "PostToolUse"
            post_payload["tool_response"] = response
            from pr_merge_gate.hook import post_run
            post_stdout = io.StringIO()
            post_stderr = io.StringIO()
            post_run(
                stdin=io.StringIO(json.dumps(post_payload)), stdout=post_stdout,
                stderr=post_stderr, audit_file=target,
            )
            records = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(calls, ["managed merge invoked once"])
        self.assertEqual(post_stdout.getvalue(), "")
        self.assertEqual([item["record_type"] for item in records], ["pre_use_decision", "post_use_completion"])
        self.assertFalse(records[0]["merge_api_called"])
        self.assertFalse(records[0]["operation_dispatched"])
        self.assertTrue(records[1]["merge_api_called"])
        self.assertTrue(records[1]["operation_dispatched"])
        self.assertEqual(records[0]["invocation_id"], records[1]["invocation_id"])
        self.assertEqual(records[1]["response_outcome"], "success")

    def connector_payload(self, event: str) -> dict:
        return {
            "session_id": "session-turn",
            "tool_use_id": "tool-turn",
            "hook_event_name": event,
            "tool_name": "mcp__codex_apps__github_merge_pull_request",
            "tool_input": {
                "repository_full_name": "example/repo",
                "pr_number": 50,
                "merge_method": "squash",
            },
        }

    def correlate(self, pre_turn, post_turn, target: Path) -> list[dict]:
        pre = self.connector_payload("PreToolUse")
        if pre_turn is not None:
            pre["turn_id"] = pre_turn
        classified = classify_pre_use(pre)
        permitted = allow_evidence()
        permitted["binding"]["operation_fingerprint"] = (
            classified.operation.operation_fingerprint
        )
        with patch(
            "pr_merge_gate.hook.resolve_github_token", return_value="token"
        ), patch(
            "pr_merge_gate.hook.evaluate_merge_operation", return_value=permitted
        ):
            stdout = io.StringIO()
            run(
                stdin=io.StringIO(json.dumps(pre)), stdout=stdout,
                stderr=io.StringIO(), audit_file=target,
            )
            self.assertEqual(stdout.getvalue(), "")
        post = self.connector_payload("PostToolUse")
        if post_turn is not None:
            post["turn_id"] = post_turn
        post["tool_response"] = {"merged": True}
        post_stdout = io.StringIO()
        post_run(
            stdin=io.StringIO(json.dumps(post)), stdout=post_stdout,
            stderr=io.StringIO(), audit_file=target,
        )
        self.assertEqual(post_stdout.getvalue(), "")
        return [
            json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()
        ]

    def test_pre_post_correlation_survives_asymmetric_turn_id(self):
        """turn_id が pre/post で揃わなくても同じ permit へ相関する（Issue #414）。

        turn_id は harness ごとに送出有無が異なる任意フィールドで、invocation_id の
        導出鍵に混ぜると同一 tool 呼び出しが pre と post で別 ID になり
        `POST_AUDIT_INTEGRITY_ERROR/PERMIT_MISSING` になる。
        """
        for pre_turn, post_turn in (
            (None, "turn-post"), ("turn-pre", None), ("turn-pre", "turn-post"), (None, None),
        ):
            with self.subTest(pre=pre_turn, post=post_turn), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "audit.jsonl"
                records = self.correlate(pre_turn, post_turn, target)
                self.assertEqual(
                    [item["record_type"] for item in records],
                    ["pre_use_decision", "post_use_completion"],
                )
                self.assertEqual(records[0]["invocation_id"], records[1]["invocation_id"])
                self.assertTrue(records[1]["operation_dispatched"])

    def test_post_use_failures_report_specific_reason_codes(self):
        """post-use の失敗経路を例外クラス名ではなく固定語彙で識別できる（Issue #414）。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            cases = []

            missing = self.connector_payload("PostToolUse")
            missing["tool_response"] = {"merged": True}
            cases.append((missing, "PERMIT_MISSING"))

            invalid = dict(missing)
            invalid.pop("tool_use_id")
            cases.append((invalid, "PAYLOAD_INVALID"))

            reclassified = self.connector_payload("PostToolUse")
            reclassified["tool_name"] = "mcp__codex_apps__github_enable_auto_merge"
            reclassified["tool_response"] = {"merged": True}
            cases.append((reclassified, "RECLASSIFIED_NOT_MERGE"))

            for payload, code in cases:
                with self.subTest(code=code):
                    stdout = io.StringIO()
                    stderr = io.StringIO()
                    result = post_run(
                        stdin=io.StringIO(json.dumps(payload)), stdout=stdout,
                        stderr=stderr, audit_file=target,
                    )
                    decision = json.loads(stdout.getvalue())
                    self.assertEqual(result, 0)
                    self.assertEqual(decision["decision"], "block")
                    self.assertIn(
                        "POST_AUDIT_INTEGRITY_ERROR/" + code, decision["reason"]
                    )
                    self.assertIn(code, stderr.getvalue())
                    self.assertNotIn("example/repo", decision["reason"])

    def test_command_rewritten_after_pre_use_is_reported_as_operation_mismatch(self):
        """別hookの `updatedInput` 書き換えを PERMIT_MISSING と混同しない（Issue #436）。

        同じ PreToolUse イベントに登録された別のhook（実測では rtk の
        `RTK auto-rewrite`）が `hookSpecificOutput.updatedInput` で `tool_input.command`
        を書き換えると、本gateが分類・permit した文字列（`gh pr merge …`）と実際に
        実行され PostToolUse に届く文字列（`rtk gh pr merge …`）がずれる。後者は
        `wrappers=["rtk"]` / `transport="cli-wrapped"` として別の
        `operation_fingerprint` になるため permit 走査が外れる。

        これは相関鍵の欠落ではなく「許可した操作と実行された操作が別物」という整合性
        違反であり、そう報告されなければ調査は毎回ログ破損の疑いへ空振りする。
        """
        pre = {
            "session_id": "session-rewrite",
            "tool_use_id": "tool-rewrite",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "gh pr merge 50 --repo example/repo --squash",
            },
        }
        classified = classify_pre_use(pre)
        self.assertEqual(classified.kind, "merge")
        self.assertEqual(classified.operation.transport, "cli-direct")
        permitted = allow_evidence()
        permitted["binding"]["operation_fingerprint"] = (
            classified.operation.operation_fingerprint
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "pr_merge_gate.hook.resolve_github_token", return_value="token"
        ), patch(
            "pr_merge_gate.hook.evaluate_merge_operation", return_value=permitted
        ):
            target = Path(directory) / "audit.jsonl"
            stdout = io.StringIO()
            run(
                stdin=io.StringIO(json.dumps(pre)), stdout=stdout,
                stderr=io.StringIO(), audit_file=target,
            )
            self.assertEqual(stdout.getvalue(), "")

            post = dict(pre)
            post["hook_event_name"] = "PostToolUse"
            post["tool_input"] = {
                "command": "rtk " + pre["tool_input"]["command"],
            }
            post["tool_response"] = {"exit_code": 0}
            rewritten = classify_pre_use(post)
            self.assertEqual(rewritten.operation.transport, "cli-wrapped")
            self.assertNotEqual(
                rewritten.operation.operation_fingerprint,
                classified.operation.operation_fingerprint,
            )

            post_stdout = io.StringIO()
            post_stderr = io.StringIO()
            post_run(
                stdin=io.StringIO(json.dumps(post)), stdout=post_stdout,
                stderr=post_stderr, audit_file=target,
            )
            decision = json.loads(post_stdout.getvalue())
            records = [
                json.loads(line)
                for line in target.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(decision["decision"], "block")
        self.assertIn(
            "POST_AUDIT_INTEGRITY_ERROR/PERMIT_OPERATION_MISMATCH", decision["reason"]
        )
        self.assertIn("PERMIT_OPERATION_MISMATCH", post_stderr.getvalue())
        self.assertNotIn("example/repo", decision["reason"])
        self.assertEqual([item["record_type"] for item in records], ["pre_use_decision"])
        self.assertTrue(records[0]["permit_issued"])

    def test_audit_integrity_failure_changes_allow_to_deny(self):
        merge = operation()
        classification = PreUseClassification(
            "merge", "CLASSIFIED", merge, merge.operation_fingerprint
        )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            target.write_text("", encoding="utf-8")
            target.chmod(0o644)
            with patch(
                "pr_merge_gate.hook.classify_pre_use", return_value=classification
            ), patch(
                "pr_merge_gate.hook.resolve_github_token", return_value="token"
            ), patch(
                "pr_merge_gate.hook.evaluate_merge_operation", return_value=allow_evidence()
            ):
                _, stdout, stderr = self.invoke(
                    {"tool_name": "mcp__codex_apps__github_merge_pull_request", "tool_input": {}},
                    target,
                )
            self.assertEqual(stderr, "")
            decision = json.loads(stdout)
            self.assertIn(
                "HOOK_INTEGRITY_ERROR",
                decision["hookSpecificOutput"]["permissionDecisionReason"],
            )

    def test_codex_config_disables_only_hosted_github_merge_tools(self):
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
        app_id = "connector_76869538009648d5b282a4bb21c3d157"
        github = config["apps"][app_id]

        self.assertNotIn("github", config["apps"])
        self.assertNotIn("enabled", github)
        self.assertNotIn("default_tools_enabled", github)
        self.assertEqual(
            set(github["tools"]),
            {"merge_pull_request", "enable_auto_merge"},
        )
        self.assertFalse(github["tools"]["merge_pull_request"]["enabled"])
        self.assertFalse(github["tools"]["enable_auto_merge"]["enabled"])

    def test_codex_and_claude_install_the_same_pre_use_gate(self):
        codex = json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
        expected_tool_names = (
            "Bash",
            "mcp__codex_apps__github_merge_pull_request",
            "mcp__codex_apps__github_enable_auto_merge",
            "mcp__github__merge_pull_request",
            "mcp__github__enable_auto_merge",
            "mcp__github__enable_pull_request_auto_merge",
            "github_merge_pull_request",
            "github_enable_auto_merge",
        )
        hosted_tool_names = (
            "codex_apps.github.merge_pull_request",
            "codex_apps.github.enable_auto_merge",
        )

        for config, script in (
            (codex, ".codex/hooks/pr-merge-gate.sh"),
            (claude, ".claude/hooks/pr-merge-gate.sh"),
        ):
            config_text = json.dumps(config)
            self.assertIn("PreToolUse", config_text)
            self.assertIn("PostToolUse", config_text)
            for event in ("PreToolUse", "PostToolUse"):
                matchers = [
                    item["matcher"]
                    for item in config["hooks"][event]
                    if script in json.dumps(item)
                ]
                self.assertEqual(len(matchers), 1)
                for tool_name in expected_tool_names:
                    self.assertIsNotNone(re.fullmatch(matchers[0], tool_name))
                for tool_name in hosted_tool_names:
                    self.assertIsNone(re.fullmatch(matchers[0], tool_name))
            self.assertIn("github_merge_pull_request", config_text)
            self.assertIn("github_enable_auto_merge", config_text)
            self.assertIn(script, config_text)
            shell = (ROOT / script).read_text(encoding="utf-8")
            self.assertIn("python3 -m pr_merge_gate.hook", shell)

    def test_codex_and_claude_scripts_actually_fire_without_actions(self):
        payload = {
            "session_id": "session-probe",
            "turn_id": "turn-probe",
            "tool_use_id": "tool-probe",
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__codex_apps__github_enable_auto_merge",
            "tool_input": {"repository_full_name": "example/repo", "pr_number": 50},
        }
        for script in (
            ROOT / ".codex/hooks/pr-merge-gate.sh",
            ROOT / ".claude/hooks/pr-merge-gate.sh",
        ):
            with self.subTest(script=script), tempfile.TemporaryDirectory() as directory:
                script_payload = dict(payload)
                if ".claude" in script.parts:
                    script_payload.pop("turn_id")
                completed = subprocess.run(
                    ["bash", str(script)], input=json.dumps(script_payload), text=True,
                    cwd=ROOT, capture_output=True,
                    env={
                        "HOME": directory,
                        "XDG_STATE_HOME": directory,
                        "CLAUDE_PROJECT_DIR": str(ROOT),
                        "PATH": __import__("os").environ["PATH"],
                    },
                    check=False,
                )
                self.assertEqual(completed.returncode, 0)
                decision = json.loads(completed.stdout)
                self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
                audit = Path(directory) / "review-system/blocker-gate/audit.jsonl"
                record = json.loads(audit.read_text(encoding="utf-8"))
                self.assertEqual(record["hook_event_id"], "tool-probe")
                self.assertTrue(record["hook_asset_hash"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
