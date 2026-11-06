"""blocker_gate の依存評価を project-status-sync の snapshot に適用する。"""

from __future__ import annotations

from typing import Any, Mapping

from blocker_gate.evaluator import (
    evaluate_closure_invariant,
    evaluate_dependencies,
    validate_graph,
)
from blocker_gate.model import IssueNode
from blocker_gate.snapshot import project_issue_snapshot


def _findings(snapshot: Mapping[str, Any], repository: str, ref: str) -> list[Any]:
    """1 Issue 分を射影して evaluator に掛ける。"""
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
