"""repository 全体の blocker snapshot（生成側/読取側で共有する閉じた契約）。

Issue #345［A］。GitHub API へ到達できない実行環境のために、Actions が
repository 全体の Issue graph を1ファイルへ書き出し、gate はそれを読んで
既存の evaluator（``blocker_gate.resolver.evaluate_snapshot``）へ流す。
判定ロジックは分岐させない——**取得経路だけ**を差し替える。

依存仕様: ``docs/methods/blocker-gate-pre-use-policy.md`` §3.3（Issue #345）と
§2.2/§2.3（IssueClass・relation の正本）。snapshot schema 自体は
``blocker-gate-snapshot/v1``（``resolver.parse_snapshot``）へ射影される。
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Mapping

from .model import ERROR_REASONS, IssueClass, POLICY_VERSION, SNAPSHOT_SCHEMA

REPOSITORY_SNAPSHOT_SCHEMA = "blocker-gate-repository-snapshot/v1"

# repository 全体を1ファイルに畳むため、投影後の node 数は既存 evaluator の
# MAX_NODES(10_000) と同じ上限で切る。超過は途中 graph を ALLOW に使わない。
MAX_PROJECTED_NODES = 10_000

_REPOSITORY = re.compile(r"^[^/\s]+/[^/\s]+$")
_ISSUE_REF = re.compile(r"^[^/\s]+/[^/#\s]+#[1-9][0-9]*$")
_ISSUE_KEYS = frozenset(
    {"node_id", "state", "blocked_by", "parent", "children", "title", "url"}
)
_TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "policy_version",
        "repository",
        "generated_at",
        "pages_complete",
        "errors",
        "issues",
    }
)
_STATES = frozenset(item.value for item in IssueClass)


class RepositorySnapshotError(ValueError):
    """snapshot を一意に解釈できないときの fail-close error。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def parse_generated_at(value: Any) -> datetime:
    """RFC3339 UTC ``Z`` の生成時刻だけを受理する（曖昧な時刻は fail-close）。"""
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RepositorySnapshotError("SNAPSHOT_TIMESTAMP_INVALID")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RepositorySnapshotError("SNAPSHOT_TIMESTAMP_INVALID") from exc
    return parsed.astimezone(timezone.utc)


def _string_refs(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not _ISSUE_REF.fullmatch(item) for item in value
    ):
        raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", label)
    if len(value) != len(set(value)):
        raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", label + " duplicate")
    return sorted(value)


def parse_repository_snapshot(raw: Any) -> dict[str, Any]:
    """生成側の出力を閉じた key/type で検証する。未知 key は素通ししない。"""
    if not isinstance(raw, dict) or set(raw) != _TOP_LEVEL_KEYS:
        raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", "top-level keys")
    if raw["schema"] != REPOSITORY_SNAPSHOT_SCHEMA:
        raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", "schema")
    if raw["policy_version"] != POLICY_VERSION:
        raise RepositorySnapshotError("SNAPSHOT_POLICY_VERSION_MISMATCH")
    repository = raw["repository"]
    if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", "repository")
    generated_at = parse_generated_at(raw["generated_at"])
    if not isinstance(raw["pages_complete"], bool):
        raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", "pages_complete")
    errors = raw["errors"]
    if (
        not isinstance(errors, list)
        or any(not isinstance(item, str) or item not in ERROR_REASONS for item in errors)
        or len(errors) != len(set(errors))
    ):
        raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", "errors")
    issues_raw = raw["issues"]
    if not isinstance(issues_raw, dict):
        raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", "issues")
    issues: dict[str, dict[str, Any]] = {}
    prefix = repository + "#"
    for ref, value in issues_raw.items():
        if not isinstance(ref, str) or not ref.startswith(prefix) or not _ISSUE_REF.fullmatch(ref):
            raise RepositorySnapshotError("SNAPSHOT_IDENTITY_INVALID", str(ref))
        if not isinstance(value, dict) or set(value) != _ISSUE_KEYS:
            raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", ref)
        node_id = value["node_id"]
        state = value["state"]
        parent = value["parent"]
        title = value["title"]
        url = value["url"]
        if not isinstance(node_id, str) or not node_id or state not in _STATES:
            raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", ref)
        if parent is not None and (
            not isinstance(parent, str) or not _ISSUE_REF.fullmatch(parent)
        ):
            raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", ref + " parent")
        # title/url は BLOCK 時の deny report 用。到達不能環境では API から
        # 引けないので snapshot に含める（欠落は診断不能な deny になるため拒否）。
        if not isinstance(title, str) or not title or not isinstance(url, str) or not url:
            raise RepositorySnapshotError("SNAPSHOT_SCHEMA_INVALID", ref + " report fields")
        issues[ref] = {
            "node_id": node_id,
            "state": state,
            "blocked_by": _string_refs(value["blocked_by"], ref + " blocked_by"),
            "parent": parent,
            "children": _string_refs(value["children"], ref + " children"),
            "title": title,
            "url": url,
        }
    return {
        "schema": REPOSITORY_SNAPSHOT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "repository": repository,
        "generated_at": raw["generated_at"],
        "generated_at_datetime": generated_at,
        "pages_complete": raw["pages_complete"],
        "errors": sorted(errors),
        "issues": issues,
    }


def _closure(issues: Mapping[str, Mapping[str, Any]], root: str) -> list[str]:
    """REST collector の ``_collect_graph`` と同じ到達集合を snapshot 上で作る。

    ``blocked_by`` ∪ ``children`` ∪ ``parent`` の到達閉包なので、集合内の
    どの node から出る辺も集合内に収まる＝``validate_graph`` の参照完全性を
    満たす。repository 全体をそのまま渡すと、無関係な Issue の relation 破損が
    対象 Issue の判定を巻き込むため、射影して切り出す。
    """
    reached: set[str] = set()
    pending = [root]
    while pending:
        ref = pending.pop()
        if ref in reached:
            continue
        reached.add(ref)
        if len(reached) > MAX_PROJECTED_NODES:
            raise RepositorySnapshotError("SNAPSHOT_GRAPH_LIMIT_EXCEEDED")
        node = issues.get(ref)
        if node is None:
            # dangling reference。ここでは補完せず、evaluator に
            # RELATION_TARGET_UNREADABLE として fail-close させる。
            continue
        pending.extend(node["blocked_by"])
        pending.extend(node["children"])
        if node["parent"] is not None:
            pending.append(node["parent"])
    return sorted(ref for ref in reached if ref in issues)


def project_issue_snapshot(
    snapshot: Mapping[str, Any], repository: str, number: int
) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    """repository snapshot から1 Issue 分の ``blocker-gate-snapshot/v1`` を作る。

    ``pages_complete``/``errors`` は repository 全体で1つしか持たないため、
    ある Issue の収集失敗が無関係な Issue まで fail-close させる。fail-close 側の
    過剰であり、意図した挙動として test で固定している（Issue #345）。
    """
    if snapshot.get("repository") != repository:
        raise RepositorySnapshotError(
            "SNAPSHOT_REPOSITORY_MISMATCH",
            f"snapshot={snapshot.get('repository')!r}; request={repository!r}",
        )
    issues = snapshot["issues"]
    root = f"{repository}#{number}"
    refs = _closure(issues, root)
    nodes = {
        ref: {
            "node_id": issues[ref]["node_id"],
            "state": issues[ref]["state"],
            "blocked_by": list(issues[ref]["blocked_by"]),
            "parent": issues[ref]["parent"],
            "children": list(issues[ref]["children"]),
        }
        for ref in refs
    }
    metadata = {
        ref: {"title": issues[ref]["title"], "html_url": issues[ref]["url"]}
        for ref in refs
    }
    projected = {
        "schema": SNAPSHOT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "mode": "issue-start",
        "repository": repository,
        "subject": {"type": "issue", "number": number},
        "roots": [root],
        "virtual_closed": [],
        "nodes": nodes,
        "pages_complete": bool(snapshot["pages_complete"]),
        "errors": list(snapshot["errors"]),
        "fetched_at": snapshot["generated_at"],
        "graphql_closing_set": [],
        "delivered_message_closing_set": [],
        "binding": {},
    }
    return projected, metadata
