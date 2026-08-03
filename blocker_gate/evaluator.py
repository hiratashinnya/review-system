"""dependency と parent/sub-issue closure の独立 evaluator。"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .model import Finding, IssueClass, IssueNode, sort_findings

MAX_NODES = 10_000
MAX_DEPTH = 100


class GraphEvaluationError(ValueError):
    def __init__(self, reason: str, path: Iterable[str] = ()) -> None:
        super().__init__(reason)
        self.reason = reason
        self.path = tuple(path)


def validate_graph(nodes: Mapping[str, IssueNode], repository: str) -> None:
    """identity、edge、双方向 parent/child、上限を fail-close 検証する。"""
    if len(nodes) > MAX_NODES:
        raise GraphEvaluationError("GRAPH_LIMIT_EXCEEDED")
    prefix = repository + "#"
    node_ids: set[str] = set()
    for ref, node in nodes.items():
        if ref != node.ref or not ref.startswith(prefix):
            raise GraphEvaluationError("IDENTITY_MISMATCH", (ref,))
        if node.node_id in node_ids:
            raise GraphEvaluationError("IDENTITY_MISMATCH", (ref,))
        node_ids.add(node.node_id)
        for target in (*node.blocked_by, *node.children):
            if target not in nodes:
                raise GraphEvaluationError("RELATION_TARGET_UNREADABLE", (ref, target))
        if node.parent is not None and node.parent not in nodes:
            raise GraphEvaluationError("RELATION_TARGET_UNREADABLE", (ref, node.parent))
        for child in node.children:
            if nodes[child].parent != ref:
                raise GraphEvaluationError("RELATION_INCONSISTENT", (ref, child))
        if node.parent is not None and ref not in nodes[node.parent].children:
            raise GraphEvaluationError("RELATION_INCONSISTENT", (node.parent, ref))
    # root の包含scope外にある blocker node も含め、取得済みgraph全体を検査する。
    # parent/children は双方向一致を上で確認済みなので children cycle の検出で
    # self relation と parent cycle の両方をfail-closeできる。
    _cycle_check(nodes, nodes, "children")
    _cycle_check(nodes, nodes, "blocked_by")


def _state(node: IssueNode, virtual_closed: frozenset[str]) -> IssueClass:
    return IssueClass.CLOSED_COMPLETED if node.ref in virtual_closed else node.state


def _cycle_check(
    nodes: Mapping[str, IssueNode], roots: Iterable[str], edge_name: str
) -> None:
    done: set[str] = set()
    active: list[str] = []

    def walk(ref: str, depth: int) -> None:
        if depth > MAX_DEPTH:
            raise GraphEvaluationError("GRAPH_LIMIT_EXCEEDED", (*active, ref))
        if ref not in nodes:
            raise GraphEvaluationError("RELATION_TARGET_UNREADABLE", (*active, ref))
        if ref in active:
            start = active.index(ref)
            raise GraphEvaluationError("GRAPH_CYCLE", (*active[start:], ref))
        if ref in done:
            return
        active.append(ref)
        node = nodes[ref]
        edges = node.blocked_by if edge_name == "blocked_by" else node.children
        for target in edges:
            walk(target, depth + 1)
        active.pop()
        done.add(ref)

    for root in roots:
        walk(root, 0)


def evaluate_dependencies(
    nodes: Mapping[str, IssueNode], roots: Iterable[str], virtual_closed: frozenset[str]
) -> list[Finding]:
    """全 direct/transitive open blocker path を列挙する。"""
    root_list = tuple(sorted(set(roots)))
    _cycle_check(nodes, root_list, "blocked_by")
    findings: list[Finding] = []

    def walk(subject: str, ref: str, path: tuple[str, ...], depth: int) -> None:
        if depth > MAX_DEPTH:
            raise GraphEvaluationError("GRAPH_LIMIT_EXCEEDED", path)
        node = nodes[ref]
        state = _state(node, virtual_closed)
        if state is IssueClass.UNKNOWN:
            findings.append(Finding("ISSUE_STATE_UNKNOWN", subject, path))
            return
        if state is not IssueClass.OPEN:
            return
        findings.append(Finding("OPEN_BLOCKER", subject, path))
        for blocker in sorted(node.blocked_by):
            walk(subject, blocker, (*path, blocker), depth + 1)

    for root in root_list:
        if root not in nodes:
            raise GraphEvaluationError("RELATION_TARGET_UNREADABLE", (root,))
        for blocker in sorted(nodes[root].blocked_by):
            walk(root, blocker, (root, blocker), 1)
    return sort_findings(findings)


def evaluate_closure_invariant(
    nodes: Mapping[str, IssueNode], roots: Iterable[str], virtual_closed: frozenset[str]
) -> list[Finding]:
    """CLOSED(parent) => all descendants CLOSED を dependency と独立評価する。"""
    scope: set[str] = set()
    for root in sorted(set(roots)):
        current: str | None = root
        depth = 0
        seen: set[str] = set()
        while current is not None:
            if current in seen:
                raise GraphEvaluationError("GRAPH_CYCLE", (*seen, current))
            if depth > MAX_DEPTH:
                raise GraphEvaluationError("GRAPH_LIMIT_EXCEEDED", (root, current))
            seen.add(current)
            scope.add(current)
            current = nodes[current].parent
            depth += 1
    _cycle_check(nodes, scope, "children")

    def add_descendants(ref: str, depth: int) -> None:
        if depth > MAX_DEPTH:
            raise GraphEvaluationError("GRAPH_LIMIT_EXCEEDED", (ref,))
        scope.add(ref)
        for child in nodes[ref].children:
            add_descendants(child, depth + 1)

    for root in tuple(scope):
        add_descendants(root, 0)

    findings: list[Finding] = []
    for parent in sorted(scope):
        parent_state = _state(nodes[parent], virtual_closed)
        if parent_state is IssueClass.UNKNOWN:
            findings.append(Finding("ISSUE_STATE_UNKNOWN", parent, (parent,)))
            continue
        if parent_state is IssueClass.OPEN:
            continue

        def inspect(ref: str, path: tuple[str, ...]) -> None:
            state = _state(nodes[ref], virtual_closed)
            if state is IssueClass.UNKNOWN:
                findings.append(Finding("ISSUE_STATE_UNKNOWN", parent, path))
            elif state is IssueClass.OPEN:
                findings.append(Finding("CLOSURE_OPEN_DESCENDANT", parent, path))
            for child in sorted(nodes[ref].children):
                inspect(child, (*path, child))

        for child in sorted(nodes[parent].children):
            inspect(child, (parent, child))
    return sort_findings(findings)
