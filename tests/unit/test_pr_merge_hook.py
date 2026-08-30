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
from pr_merge_gate.hook import _reason, post_run, run


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
        assert classified is not None
        assert classified.operation is not None
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
        assert classified is not None
        assert classified.operation is not None
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

    def test_command_rewritten_after_pre_use_still_correlates_to_the_same_pr(self):
        """透過ラッパーの `updatedInput` 書き換えで誤fail-closeしない（Issue #435 項目3）。

        同じ PreToolUse イベントに登録された別のhook（実測では rtk の
        `RTK auto-rewrite`）が `hookSpecificOutput.updatedInput` で `tool_input.command`
        を書き換えると、本gateが分類・permit した文字列（`gh pr merge …`）と実際に
        実行され PostToolUse に届く文字列（`rtk gh pr merge …`）がずれる。後者は
        `wrappers=["rtk"]` / `transport="cli-wrapped"` として別の
        `operation_fingerprint` になるため、fingerprint照合では相関が外れ、直近のマージ
        14件中13件が `PERMIT_MISSING`（PR #442以降は `PERMIT_OPERATION_MISMATCH`）へ
        落ちていた。rtkの書き換え自体はオーナー判断で不可侵なので、照合を PR identity
        （`repository` + `pr_number`）へ緩める（Issue #435 項目3・オーナー承認済み）。
        書き換えは PR identity を変えないため、相関は維持されつつ「別のPRへ差し替える」
        改竄は引き続き検知できる。
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
        assert classified is not None
        self.assertEqual(classified.kind, "merge")
        assert classified.operation is not None
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
            assert rewritten is not None
            assert rewritten.operation is not None
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
            records = [
                json.loads(line)
                for line in target.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(post_stdout.getvalue(), "")
        self.assertEqual(
            [item["record_type"] for item in records],
            ["pre_use_decision", "post_use_completion"],
        )
        self.assertTrue(records[0]["permit_issued"])
        self.assertTrue(records[1]["operation_dispatched"])
        self.assertEqual(records[0]["invocation_id"], records[1]["invocation_id"])
        self.assertEqual(records[1]["pr_number"], 50)
        self.assertFalse(records[1]["operation_fingerprint_matches_permit"])
        self.assertEqual(
            records[1]["permit_operation_fingerprint"],
            classified.operation.operation_fingerprint,
        )
        self.assertEqual(
            records[1]["operation_fingerprint"],
            rewritten.operation.operation_fingerprint,
        )

    def test_dispatch_against_a_different_pr_is_still_fail_closed(self):
        """PR identityが違えば従来どおり fail-close する（Issue #435 項目3の緩和限界）。

        緩和したのは「同じPRに対するコマンド文字列の差」だけで、**別のPRへの差し替え**は
        許可した操作と実行された操作が別物という整合性違反のまま検知する。
        """
        pre = {
            "session_id": "session-swap",
            "tool_use_id": "tool-swap",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": "gh pr merge 50 --repo example/repo --squash",
            },
        }
        classified = classify_pre_use(pre)
        assert classified is not None
        assert classified.operation is not None
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
            run(
                stdin=io.StringIO(json.dumps(pre)), stdout=io.StringIO(),
                stderr=io.StringIO(), audit_file=target,
            )

            post = dict(pre)
            post["hook_event_name"] = "PostToolUse"
            post["tool_input"] = {
                "command": "gh pr merge 51 --repo example/repo --squash",
            }
            post["tool_response"] = {"exit_code": 0}
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

    def filler(self, target: Path, count: int) -> None:
        """0600のaudit.jsonlへ `count` 件のdeny相当pre recordを積む。"""
        line = json.dumps(
            {
                "schema_version": "pr-merge-audit/5",
                "record_type": "pre_use_decision",
                "invocation_id": "filler",
                "result": "ERROR",
                "reason": "CLASSIFIER_UNKNOWN",
                "permit_issued": False,
            },
            sort_keys=True, separators=(",", ":"),
        )
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_text((line + "\n") * count, encoding="utf-8")
        target.chmod(0o600)

    def test_post_tool_use_rotates_before_the_non_merge_early_return(self):
        """非merge Bashコマンドの PostToolUse でもローテーションが起動する。

        `post_run` は「mergeと再分類できた場合」だけ完了記録へ進み、それ以外は早期
        returnする。ローテーション判定を分類の後ろに置くとマージ成立時（実測3日で14件）
        にしか起動せず、増加要因の大半を占めるdenyレコード（同期間で約330件）を抑え
        られない。分類より前に置くことをここで固定する（Issue #435 項目2）。
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            self.filler(target, 400)
            payload = {
                "session_id": "session-rotate",
                "tool_use_id": "tool-rotate",
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "gh issue view 1"},
                "tool_response": {"exit_code": 0},
            }
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = post_run(
                stdin=io.StringIO(json.dumps(payload)), stdout=stdout,
                stderr=stderr, audit_file=target,
            )
            lines = target.read_text(encoding="utf-8").splitlines()

        self.assertEqual((code, stdout.getvalue()), (0, ""))
        self.assertEqual(len(lines), 100)
        self.assertIn("AUDIT_ROTATED removed=300", stderr.getvalue())

    def test_pre_tool_use_never_rotates(self):
        """PreToolUse経路からはローテーションしない（Issue #435 項目2の設計制約）。

        permit発行前に read-modify-write を挟むと、これから相関する自分自身のpermitを
        消し得る。起動点をPostToolUseだけに閉じることで、その経路自体を作らない。
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            self.filler(target, 400)
            code, stdout, stderr = self.invoke(
                {
                    "tool_name": "mcp__codex_apps__github_enable_auto_merge",
                    "tool_input": {"repository_full_name": "example/repo", "pr_number": 50},
                },
                target,
            )
            lines = target.read_text(encoding="utf-8").splitlines()

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("AUTO_MERGE_DENIED", stdout)
        self.assertEqual(len(lines), 401)

    def test_rotation_before_classification_keeps_the_permit_and_the_completion(self):
        """ローテーションが自分のpermit/completionを消さない（Issue #435 項目2）。

        - permit（PreToolUseで既に書かれている）は `protect_invocation_id` により
          直近100件の外にあっても残る。
        - completionはローテーションより後に追記されるので、そもそも削除対象になり得ない。
        """
        payload = self.connector_payload("PreToolUse")
        classified = classify_pre_use(payload)
        assert classified is not None
        assert classified.operation is not None
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
            run(
                stdin=io.StringIO(json.dumps(payload)), stdout=io.StringIO(),
                stderr=io.StringIO(), audit_file=target,
            )
            permit_line = target.read_text(encoding="utf-8")
            filler = json.dumps(
                {
                    "record_type": "pre_use_decision",
                    "invocation_id": "filler",
                    "permit_issued": False,
                },
                sort_keys=True, separators=(",", ":"),
            )
            with target.open("a", encoding="utf-8") as handle:
                handle.write((filler + "\n") * 400)

            post = self.connector_payload("PostToolUse")
            post["tool_response"] = {"merged": True}
            post_stdout = io.StringIO()
            post_run(
                stdin=io.StringIO(json.dumps(post)), stdout=post_stdout,
                stderr=io.StringIO(), audit_file=target,
            )
            records = [
                json.loads(line)
                for line in target.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(post_stdout.getvalue(), "")
        self.assertEqual(records[0], json.loads(permit_line))
        self.assertEqual(records[-1]["record_type"], "post_use_completion")
        self.assertEqual(records[0]["invocation_id"], records[-1]["invocation_id"])
        self.assertTrue(records[-1]["operation_dispatched"])
        self.assertEqual(len(records), 102)

    def test_rotation_failure_never_blocks_an_unrelated_command(self):
        """ローテーション失敗はblockではなくstderr報告に留める（Issue #435 項目2）。

        ローテーションはpermit経路ではなく衛生処理であり、ここでblockすると merge と
        無関係なBashコマンドまで一律で止まる。auditが危険な状態なら、その後の
        `append_completion` が従来どおり fail-close する。
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            self.filler(target, 400)
            target.chmod(0o644)
            payload = {
                "session_id": "session-unsafe",
                "tool_use_id": "tool-unsafe",
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "gh issue view 1"},
                "tool_response": {"exit_code": 0},
            }
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = post_run(
                stdin=io.StringIO(json.dumps(payload)), stdout=stdout,
                stderr=stderr, audit_file=target,
            )
            lines = target.read_text(encoding="utf-8").splitlines()

        self.assertEqual((code, stdout.getvalue()), (0, ""))
        self.assertIn("AUDIT_ROTATION_SKIPPED/AUDIT_FILE_UNSAFE", stderr.getvalue())
        self.assertEqual(len(lines), 400)

    def test_post_use_failure_reports_the_skipped_unparsable_line_count(self):
        """completionが書けない経路でも破損行の読み飛ばしを可観測にする（項目1）。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_text("broken\n{\n", encoding="utf-8")
            target.chmod(0o600)
            payload = self.connector_payload("PostToolUse")
            payload["tool_response"] = {"merged": True}
            stdout = io.StringIO()
            stderr = io.StringIO()
            post_run(
                stdin=io.StringIO(json.dumps(payload)), stdout=stdout,
                stderr=stderr, audit_file=target,
            )
            decision = json.loads(stdout.getvalue())

        self.assertIn("POST_AUDIT_INTEGRITY_ERROR/PERMIT_MISSING", decision["reason"])
        self.assertNotIn("count=", decision["reason"])
        self.assertIn("AUDIT_UNPARSABLE_LINES_SKIPPED count=2", stderr.getvalue())

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

    def test_reason_block_group_states_the_merge_was_denied(self):
        """BLOCK群はマージ操作と分類済みなので「元のmerge操作は送信しません」は事実（Issue #457）。"""
        evidence = {"result": "BLOCK", "reason": "OPEN_BLOCKER", "policy_version": "1.2"}
        message = _reason(evidence)
        self.assertIn("BLOCK/OPEN_BLOCKER", message)
        self.assertIn("元のmerge操作は送信しません", message)
        self.assertIn("未解決の依存Issue", message)

    def test_reason_unclassified_group_does_not_assert_it_was_a_merge_operation(self):
        """分類不能群（CLASSIFIER_UNKNOWN等）はマージ操作だったと断定しない（Issue #457 AC）。

        「元のmerge操作は送信しません」のような断定表現を含めない——実態は
        「マージ操作かどうか確認できなかったため念のため見送った」であり、対象操作は
        マージ操作ではない可能性が高い（例: 通常の `git commit` 等が誤って
        `ERROR/CLASSIFIER_UNKNOWN` で止められるケース）。
        """
        for reason in ("CLASSIFIER_UNKNOWN", "TARGET_AMBIGUOUS", "MODE_MISMATCH"):
            with self.subTest(reason=reason):
                evidence = {"result": "ERROR", "reason": reason, "policy_version": "1.2"}
                message = _reason(evidence)
                self.assertNotIn("元のmerge操作は送信しません", message)
                self.assertIn("マージ操作と断定できなかった", message)
                self.assertIn("gitgate", message)

    def test_reason_external_error_group_states_classification_succeeded_but_check_failed(self):
        """外部要因・内部エラー群はマージ操作と分類できたが安全確認が完了できなかった旨を出す（Issue #457）。"""
        for reason, expected_detail in (
            ("API_UNAVAILABLE", "GitHub APIへの到達に失敗しました"),
            ("HOOK_INTEGRITY_ERROR", "内部整合性チェックに失敗しました"),
        ):
            with self.subTest(reason=reason):
                evidence = {"result": "ERROR", "reason": reason, "policy_version": "1.2"}
                message = _reason(evidence)
                self.assertIn(
                    "マージ操作と判定されましたが、安全確認自体を完了できませんでした", message
                )
                self.assertIn(expected_detail, message)

    def test_post_audit_integrity_error_message_includes_reason_code_meaning(self):
        """POST_AUDIT_INTEGRITY_ERROR/<code> がdocs記載の意味を要約して含む（Issue #457）。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "audit.jsonl"
            payload = self.connector_payload("PostToolUse")
            payload["tool_response"] = {"merged": True}
            stdout = io.StringIO()
            stderr = io.StringIO()
            post_run(
                stdin=io.StringIO(json.dumps(payload)), stdout=stdout,
                stderr=stderr, audit_file=target,
            )
            decision = json.loads(stdout.getvalue())

        self.assertIn("POST_AUDIT_INTEGRITY_ERROR/PERMIT_MISSING", decision["reason"])
        self.assertIn("対応するpre-use permitレコードが見つかりません", decision["reason"])
        self.assertIn("対応するpre-use permitレコードが見つかりません", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
