"""Project item の対象判定・依存評価と fail-close をまとめる。"""

from __future__ import annotations

from typing import Any, Mapping

from blocker_gate.evaluator import GraphEvaluationError
from blocker_gate.model import IssueClass
from blocker_gate.snapshot import RepositorySnapshotError

from .model import DONE, KNOWN_STATUSES, Abort, Plan, ProjectItem, SkippedItem
from .plan_decisions import plan_from_findings
from .planner_dependencies import _findings


def plan_item(
    snapshot: Mapping[str, Any],
    item: ProjectItem,
    repository: str,
    seen_warnings: set[tuple[str, str, str]],
) -> Plan:
    if item.issue_ref is None:
        return Plan(out_of_scope=1)

    node = snapshot["issues"].get(item.issue_ref)
    if node is None:
        skipped = SkippedItem(
            item.item_id,
            item.issue_ref,
            "NOT_IN_SNAPSHOT",
            "snapshot に当該 Issue が収載されていない",
        )
        return Plan(skipped=(skipped,))
    if node["state"] != IssueClass.OPEN.value or item.status == DONE:
        return Plan(out_of_scope=1)
    if item.status is None:
        skipped = SkippedItem(item.item_id, item.issue_ref, "STATUS_UNSET", "Status が未設定")
        return Plan(skipped=(skipped,))
    if item.status not in KNOWN_STATUSES:
        skipped = SkippedItem(
            item.item_id,
            item.issue_ref,
            "STATUS_UNKNOWN",
            f"遷移表に無い Status: {item.status!r}",
        )
        return Plan(skipped=(skipped,))

    try:
        findings = _findings(snapshot, repository, item.issue_ref)
    except (RepositorySnapshotError, GraphEvaluationError, KeyError, ValueError) as exc:
        reason = getattr(exc, "reason", None) or type(exc).__name__
        return Plan(abort=Abort("GRAPH_UNREADABLE", f"{item.issue_ref}: {reason}"))

    return plan_from_findings(item, findings, seen_warnings)
