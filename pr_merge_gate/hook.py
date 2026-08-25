"""Claude/Codex 共通 PR merge PreToolUse hook。"""

from __future__ import annotations

import io
import json
from pathlib import Path
import sys
from typing import Any, TextIO
import uuid

from blocker_gate.auth import resolve_github_token

from .audit import (
    AuditError,
    append_completion,
    append_decision,
    hook_asset_hash,
    rotate_records,
)
from .classifier import CLASSIFIER_VERSION, PreUseClassification, classify_pre_use
from .gate import PrMergeGateError, evaluate_merge_operation, fail_closed


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _reason(evidence: dict[str, Any]) -> str:
    return (
        "Codex AI agent PR merge gate: "
        f"{evidence['result']}/{evidence['reason']} (policy {evidence['policy_version']}); "
        "元のmerge操作は送信しません。blocker/API/hook状態を解消後に再実行してください。"
    )


def _hook_context(payload: dict[str, Any], event: str) -> tuple[str, str]:
    """interceptされたtool呼び出しのidentityを `(session_id, tool_use_id)` から導く。

    `turn_id` は鍵に含めない（Issue #414）。tool_use_id はsession内で1回のtool呼び出しに
    一意なので turn_id は識別力を足さない一方、**PreToolUse と PostToolUse で存在有無が
    揃う保証がない任意フィールド**である。鍵に混ぜると、同じtool呼び出しなのに pre と post で
    別の invocation_id が導出され、`append_completion` が permit を見つけられず
    `POST_AUDIT_INTEGRITY_ERROR/PERMIT_MISSING` になる（実測：Claude Code は PreToolUse で
    `turn_id` を送らない＝audit.jsonl の invocation_id は `uuid5(session_id\\0\\0tool_use_id)`
    と完全一致した）。
    """
    if payload.get("hook_event_name") != event:
        raise ValueError("hook_event_name")
    session_id = payload.get("session_id")
    tool_use_id = payload.get("tool_use_id")
    if not (
        isinstance(session_id, str) and session_id
        and isinstance(tool_use_id, str) and tool_use_id
    ):
        raise ValueError("hook invocation identity")
    invocation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "\0".join((session_id, tool_use_id))))
    return invocation_id, tool_use_id


def run(
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    cwd: Path | None = None,
    audit_file: Path | None = None,
) -> int:
    classification: PreUseClassification | None = None
    payload: dict[str, Any] | None = None
    invocation_id: str | None = None
    hook_event_id: str | None = None
    asset_hash: str | None = None
    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload")
        classification = classify_pre_use(payload, cwd=cwd)
        if classification is None:
            return 0
        invocation_id, hook_event_id = _hook_context(payload, "PreToolUse")
        asset_hash = hook_asset_hash()
        if classification.kind == "merge" and classification.operation is not None:
            evidence = evaluate_merge_operation(
                classification.operation, token=resolve_github_token()
            )
        else:
            evidence = fail_closed(
                classification.operation_fingerprint,
                classification.reason,
                classification.operation,
            )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        fingerprint_value = (
            classification.operation_fingerprint if classification is not None else "sha256:" + "0" * 64
        )
        evidence = fail_closed(fingerprint_value, "CLASSIFIER_UNKNOWN")
    except PrMergeGateError as exc:
        fingerprint_value = (
            classification.operation_fingerprint if classification is not None else "sha256:" + "0" * 64
        )
        operation = classification.operation if classification is not None else None
        evidence = fail_closed(fingerprint_value, exc.reason, operation)
    except AuditError:
        fingerprint_value = (
            classification.operation_fingerprint if classification is not None else "sha256:" + "0" * 64
        )
        operation = classification.operation if classification is not None else None
        evidence = fail_closed(fingerprint_value, "HOOK_INTEGRITY_ERROR", operation)
    evidence["classifier_version"] = CLASSIFIER_VERSION
    evidence["invocation_id"] = invocation_id
    evidence["hook_event_id"] = hook_event_id
    evidence["hook_asset_hash"] = asset_hash
    try:
        append_decision(evidence, path=audit_file)
    except AuditError:
        evidence = fail_closed(
            evidence["binding"]["operation_fingerprint"],
            "HOOK_INTEGRITY_ERROR",
            classification.operation if classification is not None else None,
        )
        evidence.update(
            classifier_version=CLASSIFIER_VERSION,
            invocation_id=invocation_id,
            hook_event_id=hook_event_id,
            hook_asset_hash=asset_hash,
        )
    if evidence["result"] != "ALLOW":
        json.dump(_deny(_reason(evidence)), stdout, ensure_ascii=False, separators=(",", ":"))
        stdout.write("\n")
        return 0
    stderr.write(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


def _rotate_audit(payload: dict[str, Any], audit_file: Path | None, stderr: TextIO) -> None:
    """PostToolUse経路だけでaudit.jsonlを件数ローテーションする（Issue #435 項目2）。

    **分類より前に呼ぶ**。`post_run` は「mergeと再分類できた場合」だけ完了記録へ進み、
    それ以外のBashコマンドは早期returnするので、分類の後ろに置くとマージ成立時
    （実測3日で14件）にしか起動せず、増加要因の大半を占めるdenyレコード（同期間で約330件）
    の蓄積をまったく抑えられない。PreToolUse（`run`）側からは呼ばない——permit発行前に
    read-modify-writeを挟むと、これから相関する自分自身のpermitを消し得る。

    失敗は握り潰してstderrへ出すだけにする。ローテーションはpermit経路ではなく衛生処理で
    あり、ここでblockすると **mergeと無関係なBashコマンドまで一律で止まる**。auditが実際に
    危険な状態なら、その後の `append_completion` が従来どおりfail-closeする。
    """
    try:
        protected: str | None = _hook_context(payload, "PostToolUse")[0]
    except ValueError:
        protected = None
    try:
        removed = rotate_records(protect_invocation_id=protected, path=audit_file)
    except AuditError as exc:
        stderr.write(
            "Codex AI agent PR merge gate: AUDIT_ROTATION_SKIPPED/" + exc.reason + "\n"
        )
        return
    if removed:
        stderr.write(
            f"Codex AI agent PR merge gate: AUDIT_ROTATED removed={removed}\n"
        )


def post_run(
    *, stdin: TextIO, stdout: TextIO, stderr: TextIO, cwd: Path | None = None,
    audit_file: Path | None = None,
) -> int:
    """PostToolUse responseを同じpre-use permitへ相関して監査する。"""
    try:
        payload = json.load(stdin)
        if not isinstance(payload, dict):
            raise ValueError("payload")
        _rotate_audit(payload, audit_file, stderr)
        classification = classify_pre_use(payload, cwd=cwd)
        if classification is None:
            return 0
        if classification.kind != "merge" or classification.operation is None:
            raise AuditError(
                "blocked operation reached PostToolUse", reason="RECLASSIFIED_NOT_MERGE"
            )
        invocation_id, hook_event_id = _hook_context(payload, "PostToolUse")
        tool_name = payload.get("tool_name")
        if not isinstance(tool_name, str) or "tool_response" not in payload:
            raise ValueError("post payload")
        append_completion(
            invocation_id=invocation_id,
            hook_event_id=hook_event_id,
            operation_fingerprint=classification.operation.operation_fingerprint,
            repository=classification.operation.repository,
            pr_number=classification.operation.pr_number,
            classifier_version=CLASSIFIER_VERSION,
            asset_hash=hook_asset_hash(),
            tool_name=tool_name,
            tool_response=payload["tool_response"],
            path=audit_file,
        )
        return 0
    except (AuditError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        # 例外クラス名ではなくredaction安全な固定語彙のreason codeを出す（Issue #414）。
        # `AuditError` は構造的に別物の複数経路（permit相関崩れ・再分類のずれ・hook asset
        # 読み取り不能・audit fileのmode不正・書込失敗）から送出されるため、クラス名だけでは
        # 原因を切り分けられず、報告を受けても再現なしには特定できなかった。
        code = exc.reason if isinstance(exc, AuditError) else "PAYLOAD_INVALID"
        reason = "Codex AI agent PR merge gate: POST_AUDIT_INTEGRITY_ERROR/" + code
        json.dump({"decision": "block", "reason": reason}, stdout, ensure_ascii=False)
        stdout.write("\n")
        stderr.write(reason + "\n")
        # completionを書けなかった経路では破損行のスキップをレコードに残せないので、
        # ここでstderrへ出す（Issue #435 項目1）。件数はpayload由来の文字列を含まない。
        skipped = getattr(exc, "skipped_unparsable_lines", 0)
        if skipped:
            stderr.write(
                "Codex AI agent PR merge gate: "
                f"AUDIT_UNPARSABLE_LINES_SKIPPED count={skipped}\n"
            )
        return 0


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    selected = post_run if isinstance(payload, dict) and payload.get("hook_event_name") == "PostToolUse" else run
    return selected(stdin=io.StringIO(raw), stdout=sys.stdout, stderr=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
