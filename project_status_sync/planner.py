"""snapshot ＋ Project item から `Status` の変更計画を作る（純関数・API を呼ばない）。

依存仕様: Issue #460 Scope §1。ブロッカー判定は ``blocker_gate.evaluator`` を
そのまま呼ぶ（``evaluate_dependencies`` は closed のブロッカーで再帰を打ち切るので、
``A --blocked_by--> B(closed) --blocked_by--> C(open)`` の A はブロックされない）。
親子関係は ``evaluate_closure_invariant`` が open な親を skip するため、
`Blocked` の判定材料には使わない——検出できるのは「closed の親に open の子」だけで、
それは着手を妨げる依存ではなく閉じ方の不変条件違反なので警告として扱う。

waiver（``blocker_gate.waiver``）は適用しない。board の表示は「gate が今どう
判定するか」ではなく「依存グラフが実際にどうなっているか」を映す方が誤解が少なく、
waiver 適用の可否は本 Issue のスコープ外（Issue #460 に記述がない）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

from blocker_gate.evaluator import (
    GraphEvaluationError,
    evaluate_closure_invariant,
    evaluate_dependencies,
    validate_graph,
)
from blocker_gate.model import IssueClass, IssueNode
from blocker_gate.snapshot import (
    RepositorySnapshotError,
    parse_repository_snapshot,
    project_issue_snapshot,
)

from .model import (
    ACTIVE_STATUSES,
    Abort,
    BLOCKABLE_STATUSES,
    BLOCKED,
    DONE,
    KNOWN_STATUSES,
    MAX_SNAPSHOT_AGE_SECONDS,
    Plan,
    PlannedChange,
    ProjectItem,
    READY,
    SkippedItem,
    SyncWarning,
)


def check_snapshot(
    raw: Any,
    *,
    now: datetime,
    max_age_seconds: int = MAX_SNAPSHOT_AGE_SECONDS,
) -> tuple[dict[str, Any] | None, Abort | None]:
    """snapshot 単体で決まる fail-close をすべてここで確定させる。

    Project API を1回も叩く前に呼ぶことで、「degraded / 鮮度超過なら1件も
    書かない」が検査ではなく実行順序で保証される。
    """
    try:
        snapshot = parse_repository_snapshot(raw)
    except RepositorySnapshotError as exc:
        return None, Abort("SNAPSHOT_INVALID", exc.reason if not exc.detail else f"{exc.reason}: {exc.detail}")

    if not snapshot["pages_complete"] or snapshot["errors"]:
        return snapshot, Abort(
            "SNAPSHOT_DEGRADED",
            f"pages_complete={snapshot['pages_complete']} errors={','.join(snapshot['errors']) or '-'}",
        )

    age = (now - snapshot["generated_at_datetime"]).total_seconds()
    if age > max_age_seconds:
        # degraded 判定は「壊れた snapshot」しか捕まえない。blocker-snapshot が
        # 停止して最後の publish が正常だった場合、古いブロッカー状況で書き続けて
        # しまうので、鮮度は独立に見る（Issue #460「鮮度上限」）。
        return snapshot, Abort(
            "SNAPSHOT_STALE",
            f"generated_at={snapshot['generated_at']} age={int(age)}s limit={max_age_seconds}s",
        )
    return snapshot, None


def _findings(
    snapshot: Mapping[str, Any], repository: str, ref: str
) -> list[Any]:
    """1 Issue 分を射影して evaluator に掛ける（gate と同じ手順・同じ関数）。"""
    number = int(ref.rsplit("#", 1)[1])
    projected, _ = project_issue_snapshot(snapshot, repository, number)
    nodes = {
        node_ref: IssueNode.from_dict(node_ref, value)
        for node_ref, value in projected["nodes"].items()
    }
    validate_graph(nodes, repository)
    findings = list(evaluate_dependencies(nodes, projected["roots"], frozenset()))
    findings.extend(
        evaluate_closure_invariant(nodes, projected["roots"], frozenset())
    )
    return findings


def _sorted_items(items: Iterable[ProjectItem]) -> list[ProjectItem]:
    return sorted(items, key=lambda item: (item.issue_ref or "", item.item_id))


def build_plan(
    snapshot: Mapping[str, Any],
    items: Sequence[ProjectItem],
    repository: str,
) -> Plan:
    """遷移表を適用して計画を返す。書き込みは行わない。"""
    if snapshot.get("repository") != repository:
        return Plan(
            abort=Abort(
                "SNAPSHOT_INVALID",
                f"repository mismatch: snapshot={snapshot.get('repository')!r} request={repository!r}",
            )
        )

    issues: Mapping[str, Mapping[str, Any]] = snapshot["issues"]
    changes: list[PlannedChange] = []
    skipped: list[SkippedItem] = []
    warnings: list[SyncWarning] = []
    seen_warnings: set[tuple[str, str, str]] = set()
    considered = 0
    out_of_scope = 0

    for item in _sorted_items(items):
        if item.issue_ref is None:
            # Issue 以外（PR / draft item）は Status 同期の対象外。
            out_of_scope += 1
            continue
        node = issues.get(item.issue_ref)
        if node is None:
            # snapshot（約5分間隔）と本ワークフロー（15〜30分間隔）は周期が違う
            # ので、起票直後の item がここに落ちるのは構造上必ず起きる。故障では
            # ないので赤くせず、次回実行で自動収束する。
            skipped.append(
                SkippedItem(
                    item.item_id,
                    item.issue_ref,
                    "NOT_IN_SNAPSHOT",
                    "snapshot に当該 Issue が収載されていない",
                )
            )
            continue
        if node["state"] != IssueClass.OPEN.value:
            # closed の Issue は対象外（Done を書かないことと同じ理由で触らない）。
            out_of_scope += 1
            continue
        if item.status is None:
            skipped.append(
                SkippedItem(
                    item.item_id, item.issue_ref, "STATUS_UNSET", "Status が未設定"
                )
            )
            continue
        if item.status not in KNOWN_STATUSES:
            skipped.append(
                SkippedItem(
                    item.item_id,
                    item.issue_ref,
                    "STATUS_UNKNOWN",
                    f"遷移表に無い Status: {item.status!r}",
                )
            )
            continue
        if item.status == DONE:
            out_of_scope += 1
            continue

        considered += 1
        try:
            findings = _findings(snapshot, repository, item.issue_ref)
        except (RepositorySnapshotError, GraphEvaluationError, KeyError, ValueError) as exc:
            reason = getattr(exc, "reason", None) or type(exc).__name__
            return Plan(
                abort=Abort("GRAPH_UNREADABLE", f"{item.issue_ref}: {reason}")
            )

        if any(finding.code == "ISSUE_STATE_UNKNOWN" for finding in findings):
            # 状態を読めない＝判定できない。1件も書かずに止める（fail-close）。
            return Plan(
                abort=Abort(
                    "ISSUE_STATE_UNKNOWN",
                    f"{item.issue_ref}: 依存グラフに状態不明の Issue がある",
                )
            )

        closure = [
            finding
            for finding in findings
            if finding.code == "CLOSURE_OPEN_DESCENDANT"
        ]
        if closure:
            for finding in closure:
                key = ("CLOSURE_OPEN_DESCENDANT", finding.subject, "/".join(finding.path))
                if key in seen_warnings:
                    continue
                seen_warnings.add(key)
                warnings.append(
                    SyncWarning(
                        "CLOSURE_OPEN_DESCENDANT",
                        item.issue_ref,
                        f"closed の親 {finding.subject} に open の子孫がある"
                        f"（path: {' -> '.join(finding.path)}）",
                    )
                )
            continue

        blocked = any(finding.code == "OPEN_BLOCKER" for finding in findings)

        if item.status in ACTIVE_STATUSES:
            if blocked:
                warnings.append(
                    SyncWarning(
                        "ACTIVE_ITEM_BLOCKED",
                        item.issue_ref,
                        f"Status={item.status} のままブロッカーが付いた（Status は変更しない）",
                    )
                )
            continue

        if item.status in BLOCKABLE_STATUSES and blocked:
            changes.append(
                PlannedChange(
                    item.item_id, item.issue_ref, item.status, BLOCKED, "OPEN_BLOCKER"
                )
            )
            continue
        if item.status == BLOCKED and not blocked:
            changes.append(
                PlannedChange(
                    item.item_id, item.issue_ref, item.status, READY, "BLOCKER_CLEARED"
                )
            )
            continue
        # 差分なし: Project への書き込み API は呼ばない。

    return Plan(
        changes=tuple(changes),
        skipped=tuple(skipped),
        warnings=tuple(warnings),
        abort=None,
        considered=considered,
        out_of_scope=out_of_scope,
    )
