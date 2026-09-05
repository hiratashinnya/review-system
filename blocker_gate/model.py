"""blocker gate の閉じた型と canonicalization helper。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, Mapping

# Issue #345 F-345-05（オーナー確定）: ERROR 区分内への reason 追加
# （`API_UNREACHABLE`）は §11 の規則により MINOR。1.0 → 1.1。
# Issue #363（オーナー確定・2026-08-12）: policy §3.3「材料」の trigger 記述を
# 実態（外部 cron が主たる起動元）に合わせて修正。判定意味は変えない文言修正
# のみだが §11 は文言更新も MINOR bump 対象と定めるため 1.1 → 1.2。
# Issue #466（オーナー確定・2026-09-05）: closed Issue の state reason 分類を
# 「認識済み2値以外はすべて UNKNOWN」から「closed なら解決済み側へ倒す」へ改める。
# `IssueClass` へ `CLOSED_OTHER` を追加する **型の変更**であり、同じ入力の verdict が
# `ERROR/ISSUE_STATE_UNKNOWN` から ALLOW 候補へ移る **verdict 区分をまたぐ意味変更**
# でもあるため、§11 の規則により MAJOR。1.2 → 2.0。
POLICY_VERSION = "2.0"
CLASSIFIER_VERSION = "1.0"
RESULT_SCHEMA = "blocker-gate-result/v1"
SNAPSHOT_SCHEMA = "blocker-gate-snapshot/v1"


class IssueClass(str, Enum):
    OPEN = "OPEN"
    CLOSED_COMPLETED = "CLOSED_COMPLETED"
    CLOSED_NOT_PLANNED = "CLOSED_NOT_PLANNED"
    # closed であることは確実だが、reason が認識済みの2値（COMPLETED /
    # NOT_PLANNED）のどちらでもない。`DUPLICATE`、reason 欠落（古い closed Issue）、
    # および本 policy 版が知らない将来の reason がここに入る。dependency 上の意味は
    # 他の CLOSED_* と同じ「解決済み」。
    CLOSED_OTHER = "CLOSED_OTHER"
    UNKNOWN = "UNKNOWN"


# GitHub `IssueStateReason` として policy 2.0 時点で認識している語彙（Issue #466）。
# **分類のための表ではなく、検知のための表**である——ここに無い reason 値を観測したら
# 「GitHub 側に語彙が増えた」ことを運用者へ知らせる。判定は `classify_issue_state` の
# closed/open だけで決まるので、この集合が古くなっても run は止まらない。
KNOWN_STATE_REASONS = frozenset({"COMPLETED", "NOT_PLANNED", "DUPLICATE", "REOPENED"})


def classify_issue_state(state: Any, reason: Any) -> tuple[IssueClass, str | None]:
    """GitHub の ``state``/``state reason`` を ``IssueClass`` へ写す唯一の正本。

    REST（``open``/``closed``・``not_planned``）と GraphQL（``OPEN``/``CLOSED``・
    ``NOT_PLANNED``）で大小文字だけが違うので、ここで正規化して1か所に畳む。
    判定の一次情報源を経路ごとに分岐させない（Issue #466 AC4）。

    返すのは ``(IssueClass, 認識外だった reason 値 | None)`` の2つ組。第2要素は
    **telemetry 専用**であり verdict には一切影響しない。`KNOWN_STATE_REASONS`
    に無い reason を観測したことだけを呼出側へ伝える（Issue #466 AC5 の「未知値を
    事前に分類せず、増えたことを検知する」）。

    依存仕様: ``docs/methods/blocker-gate-pre-use-policy.md`` §2.2（policy 2.0）。
    """
    if not isinstance(state, str):
        # 欠落・型不正＝状態を読めていない。fail-close は弱めない。
        return IssueClass.UNKNOWN, None
    if reason is not None and not isinstance(reason, str):
        # reason field が文字列でも null でもない＝応答が矛盾している。
        return IssueClass.UNKNOWN, None
    reason_token = reason.upper() if isinstance(reason, str) else None
    unrecognized = (
        reason_token
        if reason_token is not None and reason_token not in KNOWN_STATE_REASONS
        else None
    )
    state_token = state.upper()
    if state_token == "OPEN":
        return IssueClass.OPEN, unrecognized
    if state_token == "CLOSED":
        if reason_token == "COMPLETED":
            return IssueClass.CLOSED_COMPLETED, None
        if reason_token == "NOT_PLANNED":
            return IssueClass.CLOSED_NOT_PLANNED, None
        # GitHub が closed と返している以上、blocker としては解決済みである
        # （policy §2.2 の散文が元々そう定めていた）。reason を推測して
        # COMPLETED / NOT_PLANNED のどちらかへ寄せることはしない。
        return IssueClass.CLOSED_OTHER, unrecognized
    return IssueClass.UNKNOWN, None


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ERROR = "ERROR"


ALLOW_REASONS = frozenset({"NO_VIOLATION", "NO_CLOSING_EFFECT", "WAIVER_APPLIED"})
BLOCK_REASONS = frozenset(
    {
        "OPEN_BLOCKER",
        "CLOSURE_OPEN_DESCENDANT",
        "TARGET_ISSUE_NOT_OPEN",
        "PR_NOT_OPEN",
        "PR_DRAFT",
        "AUTO_MERGE_DENIED",
    }
)
ERROR_REASONS = frozenset(
    {
        "CLASSIFIER_UNKNOWN",
        "TARGET_AMBIGUOUS",
        "MODE_MISMATCH",
        "API_UNAVAILABLE",
        "API_PERMISSION",
        # Issue #345［B］: GitHub まで届かなかった（手前の proxy/network が
        # 遮断した）ことを、権限拒否 API_PERMISSION から分離する。
        "API_UNREACHABLE",
        "API_PARTIAL_RESPONSE",
        "PAGINATION_INCOMPLETE",
        "GRAPH_LIMIT_EXCEEDED",
        "GRAPH_CYCLE",
        "IDENTITY_MISMATCH",
        "ISSUE_STATE_UNKNOWN",
        "RELATION_INCONSISTENT",
        "RELATION_TARGET_UNREADABLE",
        "CROSS_REPOSITORY_UNSUPPORTED",
        "MERGE_METHOD_UNKNOWN",
        "MERGE_SETTINGS_AMBIGUOUS",
        "MERGE_OVERRIDE_AMBIGUOUS",
        "MERGE_MESSAGE_AMBIGUOUS",
        "REBASE_MESSAGE_AMBIGUOUS",
        "MESSAGE_SOURCE_INCOMPLETE",
        "CLOSING_KEYWORD_PARSE",
        "WAIVER_SCHEMA_INVALID",
        "WAIVER_INVALID",
        "REEVALUATION_LIMIT",
        "RESULT_CONTRACT_INVALID",
        "HOOK_INTEGRITY_ERROR",
        "INTERNAL_ERROR",
    }
)
INCOMPLETE_REASONS = frozenset(
    {
        "API_UNAVAILABLE",
        "API_PERMISSION",
        "API_UNREACHABLE",
        "API_PARTIAL_RESPONSE",
        "PAGINATION_INCOMPLETE",
        "RELATION_TARGET_UNREADABLE",
        "MESSAGE_SOURCE_INCOMPLETE",
    }
)


@dataclass(frozen=True)
class IssueNode:
    ref: str
    node_id: str
    state: IssueClass
    blocked_by: tuple[str, ...] = ()
    parent: str | None = None
    children: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, ref: str, raw: Mapping[str, Any]) -> "IssueNode":
        expected = {"node_id", "state", "blocked_by", "parent", "children"}
        if set(raw) != expected:
            raise ValueError(f"node {ref}: keys mismatch")
        return cls(
            ref=ref,
            node_id=_required_string(raw["node_id"], "node_id"),
            state=IssueClass(raw["state"]),
            blocked_by=tuple(_string_list(raw["blocked_by"], "blocked_by")),
            parent=_optional_string(raw["parent"], "parent"),
            children=tuple(_string_list(raw["children"], "children")),
        )


@dataclass(frozen=True)
class Finding:
    code: str
    subject: str
    path: tuple[str, ...]
    fingerprint: str = ""
    waiver_id: str | None = None
    waiver_evidence: Mapping[str, str] | None = None

    def finalized(self, mode: str) -> "Finding":
        digest = finding_fingerprint(self.code, mode, self.subject, self.path)
        return Finding(
            self.code,
            self.subject,
            self.path,
            digest,
            self.waiver_id,
            self.waiver_evidence,
        )

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "subject": self.subject,
            "path": list(self.path),
            "fingerprint": self.fingerprint,
            "waiver_id": self.waiver_id,
        }
        if self.waiver_evidence is not None:
            value["waiver_evidence"] = dict(self.waiver_evidence)
        return value


@dataclass(frozen=True)
class Snapshot:
    mode: str
    repository: str
    subject_type: str
    subject_number: int
    roots: tuple[str, ...]
    virtual_closed: frozenset[str]
    nodes: Mapping[str, IssueNode]
    pages_complete: bool
    errors: tuple[str, ...]
    fetched_at: str
    graphql_closing_set: tuple[str, ...] = ()
    delivered_message_closing_set: tuple[str, ...] = ()
    binding: Mapping[str, Any] = field(default_factory=dict)


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be non-empty string")
    return value


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, label)


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be string array")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} must be unique")
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def finding_fingerprint(code: str, mode: str, subject: str, path: Iterable[str]) -> str:
    return fingerprint({"code": code, "mode": mode, "path": list(path), "subject": subject})


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda item: (item.code, item.subject, item.path))
