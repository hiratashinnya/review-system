from __future__ import annotations

from typing import Mapping, Sequence

from .gate_manifest import _managed_entries
from .gate_support import IssueStartError



def _managed_transport(
    tool_name: str,
    agent_type: str,
    entries: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[Mapping[str, Any], str, Mapping[str, Any]]:
    """`entries` に一致する transport を1件だけ探す（F-354-13）。

    名前は managed 専用に見えるが、`entries` を明示すれば **`isolation_only` 区分の
    :func:`_parse_isolation_only` からも呼ばれる**——`entries=None` のときだけ
    :func:`_managed_entries` を既定にする。managed 経路と同じ「重複/欠落は fail-close」
    ロジックを isolation_only 側でも再利用するための共通化であり、isolation_only の
    entry が managed 側の shape 検証を経ていないわけではない。
    """
    matches: list[tuple[Mapping[str, Any], str, Mapping[str, Any]]] = []
    for entry in (_managed_entries() if entries is None else entries):
        if entry.get("agent_type") != agent_type:
            continue
        transports = entry.get("binding_transports")
        if not isinstance(transports, dict):
            raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
        for harness, transport in transports.items():
            if not isinstance(harness, str) or not isinstance(transport, dict):
                raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
            tool_names = transport.get("tool_names")
            if not isinstance(tool_names, list) or not all(isinstance(name, str) for name in tool_names):
                raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
            if tool_name in tool_names:
                matches.append((entry, harness, transport))
    if not matches:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", tool_name)
    if len(matches) != 1:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_AMBIGUOUS", tool_name)
    return matches[0]


def _require_transport_available(harness: str, transport: Mapping[str, Any]) -> None:
    """manifest で unavailable と宣言した稼働中transportをparser入口で拒否する。"""

    availability = transport.get("availability", "available")
    if availability == "available":
        return
    if availability != "unavailable":
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    missing = transport.get("missing_observations")
    if (
        not isinstance(missing, list)
        or not missing
        or not all(isinstance(item, str) and item for item in missing)
        or len(missing) != len(set(missing))
    ):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    raise IssueStartError(
        "ISSUE_START_TRANSPORT_UNAVAILABLE",
        f"harness={harness}; missing_observations={','.join(missing)}",
    )
