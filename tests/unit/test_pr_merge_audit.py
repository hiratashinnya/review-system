import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from pr_merge_gate.audit import (
    AuditError,
    append_completion,
    append_decision,
    audit_path,
    rotate_records,
)


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
            self.assertEqual(record["schema_version"], "pr-merge-audit/5")
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
                repository="example/repo", pr_number=50,
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
            self.assertEqual(records[1]["schema_version"], "pr-merge-audit/5")
            self.assertEqual(records[1]["skipped_unparsable_lines"], 0)
            self.assertTrue(records[1]["operation_fingerprint_matches_permit"])
            self.assertEqual(
                records[1]["permit_operation_fingerprint"], "sha256:" + "1" * 64
            )
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
                    repository="example/repo", pr_number=50,
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
                    repository="example/repo", pr_number=50,
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
        """壊れた1行でpost-use auditが恒久停止せず、読み飛ばしが無音でもない。

        Issue #414: append-onlyの共有ログには別プロセスのinterleaved writeで壊れた行が
        混じり得る。読み飛ばしはpermitを「見つけられない」方向にしか働かないため、
        permitなしでcompletionを発行する経路は増えない（fail-closeは維持）。

        Issue #435 項目1: ただし読み飛ばしを完全に無音にすると、監査証跡の完全性を
        運用者が事後検証する手段が失われる。completionレコードへ
        `skipped_unparsable_lines` として件数を残す（件数はpayload由来の文字列を
        含まないのでredactionを壊さない）。
        """
        allowed = evidence()
        allowed["result"] = "ALLOW"
        allowed["permit_issued"] = True
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(allowed, path=target)
            with target.open("a", encoding="utf-8") as handle:
                handle.write('{"record_type": "pre_use_dec\n')
                handle.write("not json at all\n")
            append_completion(
                invocation_id="invocation-1", hook_event_id="tool-1",
                operation_fingerprint="sha256:" + "1" * 64,
                repository="example/repo", pr_number=50,
                classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                tool_name="github_merge_pull_request", tool_response={"merged": True},
                path=target,
            )
            lines = target.read_text(encoding="utf-8").splitlines()
            completions = [
                json.loads(line) for line in lines if '"post_use_completion"' in line
            ]

            self.assertEqual(len(lines), 4)
            self.assertEqual(len(completions), 1)
            self.assertTrue(completions[0]["operation_dispatched"])
            self.assertEqual(completions[0]["skipped_unparsable_lines"], 2)

    def test_correlation_failure_carries_the_skipped_line_count(self):
        """completionを書けない経路でも読み飛ばし件数を失わない（Issue #435 項目1）。

        相関に失敗するとレコードが1行も増えないので、`skipped_unparsable_lines` を
        レコードへ載せる手段が無い。`AuditError` に持たせて呼び出し元（hook）が
        stderrへ出せるようにする。
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(evidence(), path=target)
            with target.open("a", encoding="utf-8") as handle:
                handle.write("broken line\n")
            with self.assertRaises(AuditError) as missing:
                append_completion(
                    invocation_id="invocation-1", hook_event_id="tool-1",
                    operation_fingerprint="sha256:" + "1" * 64,
                    repository="example/repo", pr_number=50,
                    classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                    tool_name="Bash", tool_response={"exit_code": 0}, path=target,
                )
            self.assertEqual(missing.exception.reason, "PERMIT_MISSING")
            self.assertEqual(missing.exception.skipped_unparsable_lines, 1)

    def test_audit_errors_carry_a_redaction_safe_reason_code(self):
        """AuditErrorの経路をreason codeで識別できる（Issue #414）。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            with self.assertRaises(AuditError) as missing:
                append_completion(
                    invocation_id="invocation-1", hook_event_id="tool-1",
                    operation_fingerprint="sha256:" + "1" * 64,
                    repository="example/repo", pr_number=50,
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

    def test_permit_lookup_separates_absence_from_pull_request_mismatch(self):
        """相関失敗を「permitが無い」と「別のPRが実行された」に分ける（Issue #436/#435）。

        どちらも fail-close（completionを追記しない）である点は同じだが、原因も処置も
        別物なので reason code を分ける。混同すると、実際には permit が完全な形で
        残っているのに `PERMIT_MISSING` と報告され、interleaved write によるログ破損を
        疑って調査が空振りする（Issue #436 の実測でこれが起きた）。

        Issue #435 項目3で照合対象は `operation_fingerprint` から PR identity
        （`repository` + `pr_number`）へ移った。`PERMIT_OPERATION_MISMATCH` が意味するのは
        「許可したPRと実行されたPRが別物」であり、repository違い・PR番号違いのどちらでも出る。
        """
        allowed = evidence()
        allowed["result"] = "ALLOW"
        allowed["permit_issued"] = True
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(allowed, path=target)

            for repository, pr_number in (
                ("example/repo", 51), ("example/other", 50), ("example/repo", None),
                (None, 50),
            ):
                with self.subTest(repository=repository, pr_number=pr_number):
                    with self.assertRaises(AuditError) as mismatch:
                        append_completion(
                            invocation_id="invocation-1", hook_event_id="tool-1",
                            operation_fingerprint="sha256:" + "1" * 64,
                            repository=repository, pr_number=pr_number,
                            classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                            tool_name="Bash", tool_response={"exit_code": 0}, path=target,
                        )
                    self.assertEqual(
                        mismatch.exception.reason, "PERMIT_OPERATION_MISMATCH"
                    )

            with self.assertRaises(AuditError) as absent:
                append_completion(
                    invocation_id="invocation-unknown", hook_event_id="tool-1",
                    operation_fingerprint="sha256:" + "1" * 64,
                    repository="example/repo", pr_number=50,
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
                    repository="example/repo", pr_number=50,
                    classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                    tool_name="Bash", tool_response={"exit_code": 0}, path=target,
                )
            self.assertEqual(unpermitted.exception.reason, "PERMIT_MISSING")

            self.assertEqual(
                [json.loads(line)["record_type"]
                 for line in target.read_text(encoding="utf-8").splitlines()],
                ["pre_use_decision", "pre_use_decision"],
            )

    def test_rewritten_command_still_correlates_to_the_same_pull_request(self):
        """透過ラッパーがコマンド文字列を書き換えても相関が外れない（Issue #435 項目3）。

        rtk hook が `gh pr merge …` を `rtk gh pr merge …` へ書き換えると
        `transport` が `cli-direct`→`cli-wrapped` に変わり `operation_fingerprint` が
        別物になる。以前はこれだけで相関が外れ、直近のマージ14件中13件が誤って
        fail-close していた。PR identity は書き換えで変わらないので相関は維持され、
        dispatch側とpermit側のfingerprintは両方レコードに残る。
        """
        allowed = evidence()
        allowed["result"] = "ALLOW"
        allowed["permit_issued"] = True
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(allowed, path=target)
            append_completion(
                invocation_id="invocation-1", hook_event_id="tool-1",
                operation_fingerprint="sha256:" + "e" * 64,
                repository="example/repo", pr_number=50,
                classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                tool_name="Bash", tool_response={"exit_code": 0}, path=target,
            )
            records = [
                json.loads(line)
                for line in target.read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(
            [record["record_type"] for record in records],
            ["pre_use_decision", "post_use_completion"],
        )
        self.assertTrue(records[1]["operation_dispatched"])
        self.assertEqual(records[1]["operation_fingerprint"], "sha256:" + "e" * 64)
        self.assertEqual(
            records[1]["permit_operation_fingerprint"], "sha256:" + "1" * 64
        )
        self.assertFalse(records[1]["operation_fingerprint_matches_permit"])
        self.assertEqual(records[1]["repository"], "example/repo")
        self.assertEqual(records[1]["pr_number"], 50)

    def test_corrupt_permit_line_is_absence_not_mismatch(self):
        """破損して読み飛ばされた permit は「無い」側に倒す（Issue #436）。

        読み飛ばした行の invocation_id は観測できないので、`PERMIT_OPERATION_MISMATCH`
        （＝permitは在るが別のPRだった）と主張してはならない。
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
                    repository="example/repo", pr_number=50,
                    classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                    tool_name="Bash", tool_response={"exit_code": 0}, path=target,
                )
            self.assertEqual(absent.exception.reason, "PERMIT_MISSING")
            self.assertEqual(absent.exception.skipped_unparsable_lines, 1)

    def seed(self, target: Path, count: int, *, invocation_prefix: str = "seed") -> None:
        """0600のaudit.jsonlへ `count` 件の合成pre recordを一括で置く。"""
        lines = [
            json.dumps(
                {
                    "schema_version": "pr-merge-audit/5",
                    "record_type": "pre_use_decision",
                    "invocation_id": f"{invocation_prefix}-{index}",
                    "repository": "example/repo",
                    "pr_number": 50,
                    "permit_issued": False,
                },
                sort_keys=True, separators=(",", ":"),
            )
            for index in range(count)
        ]
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.chmod(target, 0o600)

    def test_rotation_is_count_based_and_keeps_the_most_recent_records(self):
        """300件超で直近100件だけ残す（Issue #435 項目2）。

        時間基準を採らないのは、`pre_use_decision` の大半が自身のtimestampを持たず、
        現行スキーマでは保持期間を機械判定できないため（Issue #436 の実測）。
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            self.seed(target, 301)
            removed = rotate_records(path=target)
            records = [
                json.loads(line)
                for line in target.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(removed, 201)
        self.assertEqual(len(records), 100)
        self.assertEqual(records[0]["invocation_id"], "seed-201")
        self.assertEqual(records[-1]["invocation_id"], "seed-300")

    def test_rotation_is_a_no_op_below_the_threshold_or_without_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            self.assertEqual(rotate_records(path=target), 0)
            self.assertFalse(target.exists())

            self.seed(target, 300)
            self.assertEqual(rotate_records(path=target), 0)
            self.assertEqual(
                len(target.read_text(encoding="utf-8").splitlines()), 300
            )

    def test_rotation_never_drops_the_permit_of_the_protected_invocation(self):
        """自分のpermitは位置に関係なく残す＝相関を落とさない（Issue #435 項目2）。

        直近100件に入るかどうかは「ほぼ確実」でしかなく、外れた瞬間に誤
        `PERMIT_MISSING` を生む。確率ではなく構造で守るため、
        `protect_invocation_id` に一致する行は切り詰めの対象外にする。
        ローテーション後も `append_completion` が同じpermitを見つけられることまで固定する。
        """
        allowed = evidence()
        allowed["result"] = "ALLOW"
        allowed["permit_issued"] = True
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            append_decision(allowed, path=target)
            with target.open("a", encoding="utf-8") as handle:
                for index in range(400):
                    handle.write(
                        json.dumps(
                            {
                                "record_type": "pre_use_decision",
                                "invocation_id": f"other-{index}",
                                "permit_issued": False,
                            },
                            sort_keys=True, separators=(",", ":"),
                        )
                        + "\n"
                    )

            removed = rotate_records(
                protect_invocation_id="invocation-1", path=target
            )
            retained = [
                json.loads(line)
                for line in target.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(removed, 300)
            self.assertEqual(retained[0]["invocation_id"], "invocation-1")
            self.assertEqual(len(retained), 101)

            append_completion(
                invocation_id="invocation-1", hook_event_id="tool-1",
                operation_fingerprint="sha256:" + "1" * 64,
                repository="example/repo", pr_number=50,
                classifier_version="1.6", asset_hash="sha256:" + "9" * 64,
                tool_name="Bash", tool_response={"exit_code": 0}, path=target,
            )
            completions = [
                json.loads(line)
                for line in target.read_text(encoding="utf-8").splitlines()
                if '"post_use_completion"' in line
            ]
        self.assertEqual(len(completions), 1)
        self.assertTrue(completions[0]["operation_dispatched"])

    def test_rotation_rejects_an_unsafe_audit_file_instead_of_rewriting_it(self):
        """0600でないaudit fileはローテーションしない（append側と同じ安全検査）。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            self.seed(target, 400)
            os.chmod(target, 0o644)
            with self.assertRaises(AuditError) as unsafe:
                rotate_records(path=target)
            self.assertEqual(unsafe.exception.reason, "AUDIT_FILE_UNSAFE")
            self.assertEqual(
                len(target.read_text(encoding="utf-8").splitlines()), 400
            )

    def test_rotation_keeps_the_inode_so_concurrent_appends_are_not_orphaned(self):
        """切り詰めはinode差し替えではなくin-placeで行う（Issue #435 項目2）。

        `os.replace` でinodeを差し替えると、ロック解放を待っていた別プロセスのappendが
        孤立inodeへ書き込み、監査レコードが黙って失われる。同じinodeを保つことで、
        `flock` による直列化が追記と切り詰めの両方に効く。
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            self.seed(target, 400)
            before = target.stat().st_ino
            rotate_records(path=target)
            after = target.stat().st_ino
        self.assertEqual(before, after)

    def test_append_rejects_preexisting_file_with_unsafe_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            target.write_text("", encoding="utf-8")
            os.chmod(target, 0o644)
            with self.assertRaises(AuditError):
                append_decision(evidence(), path=target)


if __name__ == "__main__":
    unittest.main()
