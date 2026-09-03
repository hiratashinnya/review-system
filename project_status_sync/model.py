"""Project Status 同期の閉じた語彙と型（Issue #460）。

依存仕様: Issue #460 Scope §1（遷移表・禁止事項・鮮度上限・skipped 理由コード）と
``blocker_gate.evaluator``（ブロッカー判定の正本。本モジュールは判定を再実装しない）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REPORT_SCHEMA = "project-status-sync-report/v1"

# 読む/書く single-select field はこの1つだけ。ここを増やさない限り、
# オーナー専権 field（下記 OWNER_ONLY_FIELDS）へは構造的に書けない。
STATUS_FIELD_NAME = "Status"

INBOX = "Inbox"
READY = "Ready"
IN_PROGRESS = "In progress"
IN_REVIEW = "In review"
BLOCKED = "Blocked"
DONE = "Done"

KNOWN_STATUSES = (INBOX, READY, IN_PROGRESS, IN_REVIEW, BLOCKED, DONE)

# 進行中の作業を cron が巻き戻す競合を「検査」ではなく「構造」で消すため、
# In progress / In review は書き込み対象そのものから外す（Issue #460 Scope §1）。
ACTIVE_STATUSES = frozenset({IN_PROGRESS, IN_REVIEW})

# Blocked に入るのは {Inbox, Ready} からだけなので、解除時に Ready へ戻しても
# 情報を失わない。
BLOCKABLE_STATUSES = frozenset({INBOX, READY})

# 自動化が書いてよい遷移先はこの2つに閉じる。`Done` を含めないのは、
# built-in workflow `Auto-close issue` により Done 書き込みが Issue の close と
# 等価になるため（自動化に close 権限を持たせない）。
WRITABLE_TARGETS = frozenset({READY, BLOCKED})

# 触れてはならないオーナー専権フィールド。本ツールは STATUS_FIELD_NAME しか
# 読み書きしないので、この一覧は「守るべき対象の宣言」であり test の固定点。
OWNER_ONLY_FIELDS = ("Horizon", "Priority", "Review date", "Workstream", "Harness")

# snapshot の鮮度上限（秒）。gate の staleness 10 分は「着手を拒否してよいか」という
# 判定の鮮度を守る制約であり、本ツールの60分とは基準が別物（README「鮮度上限が60分で
# ある理由」）。本ツールが読む snapshot の鮮度を決めるのは blocker-snapshot 側の
# cadence（約5分）であって本ワークフロー自身の発火間隔ではないので、blocker-snapshot
# が健全な限り本ワークフローがいつ起動しても snapshot は0〜5分と新しい。60分は
# snapshot cadence の12周期分にあたり、一過性の揺らぎでは発火せず、blocker-snapshot
# が実際に停止した異常だけを捕まえる水準として取っている。
MAX_SNAPSHOT_AGE_SECONDS = 3600

# 遷移表に無いケース。書かず report へ理由付きで記録し、CI は赤くしない。
SKIP_REASONS = frozenset({"NOT_IN_SNAPSHOT", "STATUS_UNSET", "STATUS_UNKNOWN"})

# 書かないが CI を赤くする（故障・グラフ不整合の兆候）。
WARNING_CODES = frozenset({"ACTIVE_ITEM_BLOCKED", "CLOSURE_OPEN_DESCENDANT"})

# 1件も書かず CI を赤くする（fail-close）。
ABORT_CODES = frozenset(
    {
        "SNAPSHOT_INVALID",
        "SNAPSHOT_DEGRADED",
        "SNAPSHOT_STALE",
        "GRAPH_UNREADABLE",
        "ISSUE_STATE_UNKNOWN",
        "PROJECT_UNREADABLE",
        "APPLY_FAILED",
    }
)

CHANGE_REASONS = frozenset({"OPEN_BLOCKER", "BLOCKER_CLEARED"})


@dataclass(frozen=True)
class ProjectItem:
    """Project の item 1件。``issue_ref`` は対象 repository の Issue のときだけ入る。"""

    item_id: str
    issue_ref: str | None
    status: str | None
    content_type: str = "Issue"


@dataclass(frozen=True)
class ProjectView:
    """Project から read-only で引いた、同期に必要な最小の状態。"""

    project_id: str
    number: int
    title: str
    status_field_id: str
    status_option_ids: dict[str, str]
    items: tuple[ProjectItem, ...]


@dataclass(frozen=True)
class PlannedChange:
    item_id: str
    issue_ref: str
    from_status: str
    to_status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "issue_ref": self.issue_ref,
            "from": self.from_status,
            "to": self.to_status,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SkippedItem:
    item_id: str
    issue_ref: str | None
    code: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "issue_ref": self.issue_ref,
            "code": self.code,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class SyncWarning:
    code: str
    issue_ref: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "issue_ref": self.issue_ref, "detail": self.detail}


@dataclass(frozen=True)
class Abort:
    code: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class Plan:
    """dry-run でも apply でも同じ計画。``abort`` があるとき changes は必ず空。"""

    changes: tuple[PlannedChange, ...] = ()
    skipped: tuple[SkippedItem, ...] = ()
    warnings: tuple[SyncWarning, ...] = ()
    abort: Abort | None = None
    considered: int = 0
    out_of_scope: int = 0
