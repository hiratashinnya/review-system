import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from pr_merge_gate.audit import AuditError, append_completion, append_decision, audit_path


def evidence() -> dict:
    return {
        "policy_version": "pr-merge-pre-use/1",
        "classifier_version": "1.6",
        "hook_asset_hash": "sha256:" + "9" * 64,
        "hook_event_id": "tool-1",
        "invocation_id": "invocation-1",
        "result": "DENY",
        "reason": "BLOCKER_VIOLATION",
        "binding": {
            "repository": "example/repo",
            "pr_number": 50,
            "merge_method": "squash",
            "transport": "connector",
            "operation_fingerprint": "sha256:" + "1" * 64,
            "head_oid": "a" * 40,
            "expected_commit_count": 3,
            "base_ref_name": "main",
            "default_branch": "main",
            "intercepted_commit_title_fingerprint": "sha256:" + "3" * 64,
            "intercepted_commit_message_fingerprint": "sha256:" + "4" * 64,
            "message_source_fingerprint": "sha256:" + "5" * 64,
            "delivered_message_fingerprint": "sha256:" + "6" * 64,
            "repository_merge_settings_fingerprint": "sha256:" + "7" * 64,
            "snapshot_fingerprint": "sha256:" + "8" * 64,
            "attempt": 2,
            "pr_state": "OPEN",
            "pr_is_draft": False,
        },
        "blocker_evidence": {
            "invocation_id": "inv-1",
            "policy_version": "1.0",
            "classifier_version": "blocker-gate/1",
            "result": "BLOCK",
            "reasons": ["OPEN_BLOCKER"],
            "completed_at": "2026-08-10T00:00:01Z",
            "pages_complete": True,
        },
        "graphql_closing_set": ["example/repo#7"],
        "delivered_message_closing_set": ["example/repo#8"],
        "closing_set": ["example/repo#7", "example/repo#8"],
        "findings": [
            {
                "code": "OPEN_BLOCKER", "subject": "example/repo#7",
                "path": ["example/repo#7", "example/repo#6"],
                "fingerprint": "sha256:" + "2" * 64, "waiver_id": None,
            }
        ],
        "fetched_at": "2026-08-10T00:00:00Z",
        "permit_issued": False,
        "next_action": "fix blockers",
        "raw_command": "gh pr merge 50 --body secret",
        "token": "secret",
    }


class AuditTest(unittest.TestCase):
    def test_audit_path_prefers_xdg_and_rejects_relative_root(self):
        self.assertEqual(
            audit_path({"XDG_STATE_HOME": "/tmp/state"}),
            Path("/tmp/state/review-system/blocker-gate/audit.jsonl"),
        )
        with self.assertRaises(AuditError):
            audit_path({"XDG_STATE_HOME": "relative"})

    def test_append_is_private_durable_jsonl_without_raw_input(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state" / "audit.jsonl"
            append_decision(evidence(), path=target)
            record = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(target.parent.stat().st_mode), 0o700)
            self.assertEqual(record["reason"], "BLOCKER_VIOLATION")
            self.assertFalse(record["merge_api_called"])
            self.assertFalse(record["operation_dispatched"])
            self.assertEqual(record["head_oid"], "a" * 40)
            self.assertEqual(record["expected_commit_count"], 3)
            self.assertEqual(record["base_ref_name"], "main")
            self.assertEqual(record["default_branch"], "main")
            self.assertEqual(record["schema_version"], "pr-merge-audit/4")
            self.assertEqual(record["attempt"], 2)
            self.assertEqual(record["pr_state"], "OPEN")
            self.assertFalse(record["pr_is_draft"])
            for key, digit in (
                ("intercepted_commit_title_fingerprint", "3"),
                ("intercepted_commit_message_fingerprint", "4"),
                ("message_source_fingerprint", "5"),
                ("delivered_message_fingerprint", "6"),
                ("repository_merge_settings_fingerprint", "7"),
                ("snapshot_fingerprint", "8"),
            ):
                self.assertEqual(record[key], "sha256:" + digit * 64)
            self.assertEqual(record["blocker_reasons"], ["OPEN_BLOCKER"])
            self.assertTrue(record["pages_complete"])
            self.assertEqual(
                record["delivered_message_formatter_version"],
                "github-delivered-message/2",
            )
            self.assertFalse(record["squash_commit_messages_verified"])
            self.assertEqual(record["squash_commit_messages_decision"], "fail-close")
            self.assertEqual(record["closing_set"], ["example/repo#7", "example/repo#8"])
            self.assertEqual(record["dependency_paths"], [["example/repo#7", "example/repo#6"]])
            self.assertEqual(record["classifier_version"], "1.6")
            self.assertEqual(record["hook_event_id"], "tool-1")
            serialized = json.dumps(record)
            self.assertNotIn("secret", serialized)
            self.assertNotIn("raw_command", serialized)

    def test_completion_requires_matching_permit_and_redacts_response(self):
        allowed = evidence()
        allowed["result"] = "ALLOW"
        allowed["permit_issued"] = True
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(allowed, path=target)
            append_completion(
                invocation_id="invocation-1", hook_event_id="tool-1",
                operation_fingerprint="sha256:" + "1" * 64,
                classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                tool_name="github_merge_pull_request",
                tool_response={
                    "structuredContent": {
                        "result": {"merged": True, "message": "sensitive-response"}
                    }
                },
                path=target,
            )
            records = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(records[1]["record_type"], "post_use_completion")
            self.assertTrue(records[1]["merge_api_called"])
            self.assertTrue(records[1]["operation_dispatched"])
            self.assertEqual(records[1]["response_outcome"], "success")
            self.assertEqual(records[1]["schema_version"], "pr-merge-audit/4")
            self.assertEqual(records[1]["head_oid"], "a" * 40)
            self.assertEqual(records[1]["expected_commit_count"], 3)
            self.assertEqual(records[1]["attempt"], 2)
            self.assertEqual(records[1]["snapshot_fingerprint"], "sha256:" + "8" * 64)
            self.assertEqual(
                records[1]["closing_set"],
                ["example/repo#7", "example/repo#8"],
            )
            self.assertFalse(records[1]["squash_commit_messages_verified"])
            self.assertNotIn("sensitive-response", json.dumps(records[1]))
            with self.assertRaises(AuditError):
                append_completion(
                    invocation_id="missing", hook_event_id="tool-2",
                    operation_fingerprint="sha256:" + "1" * 64,
                    classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                    tool_name="github_merge_pull_request", tool_response={}, path=target,
                )

    def test_completion_does_not_infer_api_call_from_cli_or_failed_connector(self):
        cases = (
            ("cli-direct", {"exit_code": 0}, "success"),
            ("cli-wrapped", {"exit_code": 2}, "failure"),
            ("rest", {"exit_code": 1}, "failure"),
            ("connector", {"isError": True}, "failure"),
            ("connector", {"merged": False}, "failure"),
            ("connector", {"message": "result shape unknown"}, "unknown"),
        )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            for index, (transport, response, outcome) in enumerate(cases, start=1):
                allowed = evidence()
                allowed["result"] = "ALLOW"
                allowed["permit_issued"] = True
                allowed["invocation_id"] = f"invocation-{index}"
                allowed["binding"]["transport"] = transport
                allowed["binding"]["operation_fingerprint"] = "sha256:" + str(index) * 64
                append_decision(allowed, path=target)
                append_completion(
                    invocation_id=f"invocation-{index}", hook_event_id=f"tool-{index}",
                    operation_fingerprint="sha256:" + str(index) * 64,
                    classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                    tool_name=(
                        "github_merge_pull_request" if transport == "connector" else "Bash"
                    ),
                    tool_response=response, path=target,
                )
            completions = [
                json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()
                if '"post_use_completion"' in line
            ]
        self.assertEqual(len(completions), len(cases))
        for completion, (_, _, outcome) in zip(completions, cases):
            self.assertTrue(completion["operation_dispatched"])
            self.assertIsNone(completion["merge_api_called"])
            self.assertEqual(completion["merge_api_call_evidence"], "NOT_PROVEN")
            self.assertEqual(completion["response_outcome"], outcome)

    def test_completion_scan_skips_corrupt_lines_without_losing_the_permit(self):
        """壊れた1行でpost-use auditが恒久停止しない（Issue #414）。

        append-onlyの共有ログには別プロセスのinterleaved writeで壊れた行が混じり得る。
        読み飛ばしはpermitを「見つけられない」方向にしか働かないため、permitなしで
        completionを発行する経路は増えない（fail-closeは維持）。
        """
        allowed = evidence()
        allowed["result"] = "ALLOW"
        allowed["permit_issued"] = True
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(allowed, path=target)
            with target.open("a", encoding="utf-8") as handle:
                handle.write('{"record_type": "pre_use_dec\n')
            append_completion(
                invocation_id="invocation-1", hook_event_id="tool-1",
                operation_fingerprint="sha256:" + "1" * 64,
                classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                tool_name="github_merge_pull_request", tool_response={"merged": True},
                path=target,
            )
            lines = target.read_text(encoding="utf-8").splitlines()
            completions = [
                json.loads(line) for line in lines if '"post_use_completion"' in line
            ]

            self.assertEqual(len(lines), 3)
            self.assertEqual(len(completions), 1)
            self.assertTrue(completions[0]["operation_dispatched"])

    def test_audit_errors_carry_a_redaction_safe_reason_code(self):
        """AuditErrorの経路をreason codeで識別できる（Issue #414）。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            with self.assertRaises(AuditError) as missing:
                append_completion(
                    invocation_id="invocation-1", hook_event_id="tool-1",
                    operation_fingerprint="sha256:" + "1" * 64,
                    classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                    tool_name="github_merge_pull_request", tool_response={}, path=target,
                )
            self.assertEqual(missing.exception.reason, "PERMIT_MISSING")

            target.write_text("", encoding="utf-8")
            os.chmod(target, 0o644)
            with self.assertRaises(AuditError) as unsafe:
                append_decision(evidence(), path=target)
            self.assertEqual(unsafe.exception.reason, "AUDIT_FILE_UNSAFE")

        with self.assertRaises(AuditError) as relative:
            audit_path({"XDG_STATE_HOME": "relative"})
        self.assertEqual(relative.exception.reason, "AUDIT_PATH_INVALID")

    def test_permit_lookup_separates_absence_from_operation_mismatch(self):
        """相関失敗を「permitが無い」と「別の操作が実行された」に分ける（Issue #436）。

        どちらも fail-close（completionを追記しない）である点は同じだが、原因も処置も
        別物なので reason code を分ける。混同すると、実際には permit が完全な形で
        残っているのに `PERMIT_MISSING` と報告され、interleaved write によるログ破損を
        疑って調査が空振りする（Issue #436 の実測でこれが起きた）。
        """
        allowed = evidence()
        allowed["result"] = "ALLOW"
        allowed["permit_issued"] = True
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(allowed, path=target)

            with self.assertRaises(AuditError) as mismatch:
                append_completion(
                    invocation_id="invocation-1", hook_event_id="tool-1",
                    operation_fingerprint="sha256:" + "f" * 64,
                    classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                    tool_name="Bash", tool_response={"exit_code": 0}, path=target,
                )
            self.assertEqual(mismatch.exception.reason, "PERMIT_OPERATION_MISMATCH")

            with self.assertRaises(AuditError) as absent:
                append_completion(
                    invocation_id="invocation-unknown", hook_event_id="tool-1",
                    operation_fingerprint="sha256:" + "1" * 64,
                    classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                    tool_name="Bash", tool_response={"exit_code": 0}, path=target,
                )
            self.assertEqual(absent.exception.reason, "PERMIT_MISSING")

            denied = evidence()
            denied["invocation_id"] = "invocation-denied"
            append_decision(denied, path=target)
            with self.assertRaises(AuditError) as unpermitted:
                append_completion(
                    invocation_id="invocation-denied", hook_event_id="tool-1",
                    operation_fingerprint="sha256:" + "1" * 64,
                    classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                    tool_name="Bash", tool_response={"exit_code": 0}, path=target,
                )
            self.assertEqual(unpermitted.exception.reason, "PERMIT_MISSING")

            self.assertEqual(
                [json.loads(line)["record_type"]
                 for line in target.read_text(encoding="utf-8").splitlines()],
                ["pre_use_decision", "pre_use_decision"],
            )

    def test_corrupt_permit_line_is_absence_not_mismatch(self):
        """破損して読み飛ばされた permit は「無い」側に倒す（Issue #436）。

        読み飛ばした行の invocation_id は観測できないので、`PERMIT_OPERATION_MISMATCH`
        （＝permitは在るが操作が違う）と主張してはならない。
        """
        allowed = evidence()
        allowed["result"] = "ALLOW"
        allowed["permit_issued"] = True
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(allowed, path=target)
            corrupted = target.read_text(encoding="utf-8")[:-40] + "\n"
            target.write_text(corrupted, encoding="utf-8")
            with self.assertRaises(AuditError) as absent:
                append_completion(
                    invocation_id="invocation-1", hook_event_id="tool-1",
                    operation_fingerprint="sha256:" + "1" * 64,
                    classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                    tool_name="Bash", tool_response={"exit_code": 0}, path=target,
                )
            self.assertEqual(absent.exception.reason, "PERMIT_MISSING")

    def test_append_rejects_preexisting_file_with_unsafe_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            target.write_text("", encoding="utf-8")
            os.chmod(target, 0o644)
            with self.assertRaises(AuditError):
                append_decision(evidence(), path=target)


if __name__ == "__main__":
    unittest.main()
