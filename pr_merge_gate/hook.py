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


# reason codeの正本＝docs/methods/blocker-gate-pre-use-policy.md §10.2。
# `_reason()` は評価根拠（BLOCK/ERROR）と reason に応じて群を分け、
# 「マージ操作と分類できたか」「分類できた場合ポリシー違反かどうか」で
# メッセージの断定表現を出し分ける（Issue #457）。

# BLOCK群：マージ操作と分類され、ポリシー上ブロックされた（"元のmerge操作は送信しません"は事実）。
_BLOCK_REASONS = frozenset(
    {
        "OPEN_BLOCKER",
        "CLOSURE_OPEN_DESCENDANT",
        "TARGET_ISSUE_NOT_OPEN",
        "PR_NOT_OPEN",
        "PR_DRAFT",
        "AUTO_MERGE_DENIED",
    }
)

# 分類不能群：マージ操作かどうか自体を確認できなかった（マージ操作ではない可能性が高い）。
_UNCLASSIFIED_REASONS = frozenset(
    {
        "CLASSIFIER_UNKNOWN",
        "TARGET_AMBIGUOUS",
        "MODE_MISMATCH",
    }
)

# 上記2群以外のERROR reason（docs/methods/blocker-gate-pre-use-policy.md §10.2のERROR一覧から
# BLOCK群・分類不能群を除いたもの）は「マージ操作と分類はできたが、安全確認自体が完了できなかった」
# 外部要因・内部エラー群として扱う。

_REASON_DETAILS: dict[str, str] = {
    # BLOCK群
    "OPEN_BLOCKER": "未解決の依存Issue（blocked-by）が残っています。",
    "CLOSURE_OPEN_DESCENDANT": "親Issueをcloseする一方で子Issueが未解決のままです。",
    "TARGET_ISSUE_NOT_OPEN": "対象Issueがopen状態ではありません。",
    "PR_NOT_OPEN": "対象PRがopen状態ではありません。",
    "PR_DRAFT": "対象PRがdraftのままです。",
    "AUTO_MERGE_DENIED": "auto-mergeの有効化はこのゲートで常に拒否します。",
    # 分類不能群
    "CLASSIFIER_UNKNOWN": "コマンドがマージ操作かどうかをclassifierが確定できませんでした。",
    "TARGET_AMBIGUOUS": "対象repository/PR/Issueを一意に確定できませんでした。",
    "MODE_MISMATCH": "issue-startとpr-mergeのどちらの操作か確定できませんでした。",
    # 外部要因・内部エラー群
    "API_UNAVAILABLE": "GitHub APIへの到達に失敗しました（429/5xxまたはretry枯渇）。",
    "API_PERMISSION": "GitHubが認可を拒否しました（401/403、GitHub発信）。",
    "API_UNREACHABLE": "GitHubまで応答が届いていません（proxy/tunnel/DNS/timeout等）。",
    "API_PARTIAL_RESPONSE": "GraphQLの応答が部分的でした。",
    "PAGINATION_INCOMPLETE": "pagination（cursor/page）を完走できませんでした。",
    "GRAPH_LIMIT_EXCEEDED": "依存グラフの探索上限を超えました。",
    "GRAPH_CYCLE": "依存関係に循環を検出しました。",
    "IDENTITY_MISMATCH": "取得内容がintercept時の識別情報と一致しません。",
    "ISSUE_STATE_UNKNOWN": "Issueの状態を判定できませんでした。",
    "RELATION_INCONSISTENT": "parent/sub-issueの関係が双方向で一致しません。",
    "RELATION_TARGET_UNREADABLE": "関係先のnodeを読み取れませんでした（削除・非可視等）。",
    "CROSS_REPOSITORY_UNSUPPORTED": "リポジトリをまたぐ関係はこのゲートの対象外です。",
    "MERGE_METHOD_UNKNOWN": "merge methodを一意に確定できませんでした。",
    "MERGE_SETTINGS_AMBIGUOUS": "repositoryのmerge設定を一意に再構築できませんでした。",
    "MERGE_OVERRIDE_AMBIGUOUS": "commit title/bodyのoverrideを一意に束縛できませんでした。",
    "MERGE_MESSAGE_AMBIGUOUS": "merge/squash commit messageを一意に再構築できませんでした。",
    "REBASE_MESSAGE_AMBIGUOUS": "rebase後に届くcommit messageを一意に決定できませんでした。",
    "MESSAGE_SOURCE_INCOMPLETE": "commit messageの取得元が不完全でした。",
    "CLOSING_KEYWORD_PARSE": "closing keywordの構文解析に失敗しました。",
    "WAIVER_SCHEMA_INVALID": "waiverファイルのschemaが不正です。",
    "WAIVER_INVALID": "waiverの真正性検証に失敗しました。",
    "REEVALUATION_LIMIT": "再評価3回でも状態が安定しませんでした。",
    "RESULT_CONTRACT_INVALID": "判定結果がschema/semantic契約を満たしませんでした。",
    "HOOK_INTEGRITY_ERROR": "hook自身の監査書き込み等、内部整合性チェックに失敗しました。",
    "INTERNAL_ERROR": "hook内部で想定外の例外が発生しました。",
}


def _reason(evidence: dict[str, Any]) -> str:
    result = evidence["result"]
    reason = evidence["reason"]
    header = (
        "Codex AI agent PR merge gate: "
        f"{result}/{reason} (policy {evidence['policy_version']});"
    )
    detail = _REASON_DETAILS.get(reason)
    detail_part = f" {detail}" if detail else ""

    if reason in _UNCLASSIFIED_REASONS:
        # マージ操作と断定していないことを表す（「元のmerge操作は送信しません」のような
        # 断定表現は使わない）。実態は「マージ操作かどうか確認できなかったため念のため
        # 実行を見送った」であり、マージ操作でない可能性が高い（Issue #457）。
        return (
            f"{header}{detail_part} "
            "元の操作をマージ操作と断定できなかったため、念のため実行を見送りました"
            "（実際にはマージ操作ではない可能性があります）。マージ操作でない場合は、"
            "コマンドをより単純な1行の形に書き直すか、`python3 -m gitgate` 経由の"
            "操作を使って再実行してください。マージ操作である場合は、blocker/API/"
            "hook状態を解消後に再実行してください。"
        )
    if reason in _BLOCK_REASONS:
        return (
            f"{header}{detail_part} "
            "マージ操作と判定され、ポリシー違反のため元のmerge操作は送信しません。"
            "上記の状況を解消してから再実行してください。"
        )
    # 外部要因・内部エラー群（マージ操作と分類はできたが、安全確認自体が完了できなかった）。
    # 未知のreason（policy改訂の取りこぼし等）もdetailなしでこの群として扱う——
    # マージ操作と分類できた経路（BLOCK/ERROR双方が通る evaluate_merge_operation・
    # append_decision失敗時のHOOK_INTEGRITY_ERROR）から来るためBLOCK群と同じ断定はできないが、
    # 分類不能群のように「マージ操作ではない可能性が高い」とも言えない。
    return (
        f"{header}{detail_part} "
        "マージ操作と判定されましたが、安全確認自体を完了できませんでした。"
        "元のmerge操作は送信しません。API到達性やhookの状態を確認のうえ再実行してください。"
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


# PostToolUse失敗のreason code説明（正本＝docs/tools/pr-merge-gate.md「PostToolUse失敗の
# reason code」表・Issue #414/#436）。POST_AUDIT_INTEGRITY_ERROR/<code> のメッセージへ要約を
# 含める（Issue #457）。
_POST_AUDIT_REASON_DETAILS: dict[str, str] = {
    "PAYLOAD_INVALID": (
        "payloadがJSONでない、または必須フィールド"
        "（hook_event_name/session_id/tool_use_id/tool_name/tool_response）が"
        "契約を満たしていません。"
    ),
    "RECLASSIFIED_NOT_MERGE": (
        "PreToolUseでdenyされたはずの操作がPostToolUseへ到達し、"
        "再分類でmerge操作と判定できませんでした。"
    ),
    "PERMIT_MISSING": (
        "対応するpre-use permitレコードが見つかりません"
        "（auditファイル不在／pre-use hook未発火／該当行が破損して読み飛ばされた、のいずれか）。"
    ),
    "PERMIT_OPERATION_MISMATCH": (
        "permitはありますが、許可したPRと実行されたPRが別物です。"
    ),
    "HOOK_ASSET_UNREADABLE": "hook asset一式のhash計算に失敗しました。",
    "AUDIT_FILE_UNSAFE": (
        "audit fileがsymlink・別uid所有・0600以外のいずれかで安全ではありません。"
    ),
    "AUDIT_PATH_INVALID": (
        "HOME/XDG_STATE_HOMEが未設定、または絶対パスではありません。"
    ),
    "AUDIT_READ_FAILED": "audit fileの読み取りがOSレベルで失敗しました。",
    "AUDIT_WRITE_FAILED": "audit fileの書き込みがOSレベルで失敗しました。",
}


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
        detail = _POST_AUDIT_REASON_DETAILS.get(code)
        detail_part = f" {detail}" if detail else ""
        reason = (
            "Codex AI agent PR merge gate: POST_AUDIT_INTEGRITY_ERROR/" + code + ";" + detail_part
        )
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
