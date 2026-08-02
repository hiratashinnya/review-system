"""Issue/PR adapter 共通の snapshot resolver。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, cast
from uuid import uuid4

from .contract import ContractError, validate_result_semantics
from .evaluator import (
    GraphEvaluationError,
    evaluate_closure_invariant,
    evaluate_dependencies,
    validate_graph,
)
from .model import (
    ALLOW_REASONS,
    BLOCK_REASONS,
    CLASSIFIER_VERSION,
    ERROR_REASONS,
    INCOMPLETE_REASONS,
    POLICY_VERSION,
    RESULT_SCHEMA,
    SNAPSHOT_SCHEMA,
    Finding,
    IssueClass,
    IssueNode,
    Snapshot,
    Verdict,
    fingerprint,
    sort_findings,
)
from .waiver import (
    WaiverCollection,
    WaiverContext,
    WaiverError,
    WaiverMaterial,
    parse_policy_yaml,
    parse_waiver_yaml,
    verify_waiver,
)


class Collector(Protocol):
    """GitHub API 取得 adapter。書込みメソッドを持たない。"""

    def collect_issue(self, repository: str, number: int) -> Mapping[str, Any]: ...

    def collect_pull_request(
        self, repository: str, number: int, merge_method: str
    ) -> Mapping[str, Any]: ...


class WaiverProvider(Protocol):
    def collect_waiver_materials(self, repository: str) -> WaiverCollection: ...


def _timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_snapshot(raw: Mapping[str, Any]) -> Snapshot:
    required = {
        "schema",
        "policy_version",
        "mode",
        "repository",
        "subject",
        "roots",
        "virtual_closed",
        "nodes",
        "pages_complete",
        "errors",
        "fetched_at",
        "graphql_closing_set",
        "delivered_message_closing_set",
        "binding",
    }
    if set(raw) != required:
        raise ValueError("snapshot keys mismatch")
    if raw["schema"] != SNAPSHOT_SCHEMA or raw["policy_version"] != POLICY_VERSION:
        raise ValueError("snapshot version mismatch")
    mode = raw["mode"]
    if mode not in {"issue-start", "pr-merge"}:
        raise ValueError("mode mismatch")
    subject = raw["subject"]
    if not isinstance(subject, dict) or set(subject) != {"type", "number"}:
        raise ValueError("subject invalid")
    expected_type = "issue" if mode == "issue-start" else "pull_request"
    if subject["type"] != expected_type or not isinstance(subject["number"], int) or subject["number"] < 1:
        raise ValueError("subject invalid")
    repository = raw["repository"]
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise ValueError("repository invalid")
    nodes_raw = raw["nodes"]
    if not isinstance(nodes_raw, dict):
        raise ValueError("nodes invalid")
    nodes = {ref: IssueNode.from_dict(ref, value) for ref, value in nodes_raw.items()}
    roots = _unique_refs(raw["roots"], "roots")
    virtual = frozenset(_unique_refs(raw["virtual_closed"], "virtual_closed"))
    graphql = tuple(_unique_refs(raw["graphql_closing_set"], "graphql_closing_set"))
    delivered = tuple(
        _unique_refs(raw["delivered_message_closing_set"], "delivered_message_closing_set")
    )
    errors = tuple(_unique_reasons(raw["errors"]))
    if not isinstance(raw["pages_complete"], bool):
        raise ValueError("pages_complete invalid")
    if not isinstance(raw["fetched_at"], str):
        raise ValueError("fetched_at invalid")
    if not isinstance(raw["binding"], dict):
        raise ValueError("binding invalid")
    if mode == "issue-start" and (virtual or graphql or delivered):
        raise ValueError("issue snapshot contains PR fields")
    if mode == "pr-merge" and set(roots) != set(graphql) | set(delivered):
        raise ValueError("closing set union mismatch")
    return Snapshot(
        mode=mode,
        repository=repository,
        subject_type=expected_type,
        subject_number=subject["number"],
        roots=tuple(sorted(roots)),
        virtual_closed=virtual,
        nodes=nodes,
        pages_complete=raw["pages_complete"],
        errors=errors,
        fetched_at=raw["fetched_at"],
        graphql_closing_set=tuple(sorted(graphql)),
        delivered_message_closing_set=tuple(sorted(delivered)),
        binding=dict(raw["binding"]),
    )


def _unique_refs(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{label} invalid")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} duplicate")
    return tuple(value)


def _unique_reasons(value: Any) -> tuple[str, ...]:
    values = _unique_refs(value, "errors")
    if any(item not in ERROR_REASONS for item in values):
        raise ValueError("unknown error reason")
    return values


def _binding(snapshot: Snapshot) -> dict[str, Any]:
    keys = {
        "head_oid",
        "base_ref_name",
        "default_branch",
        "merge_method",
        "intercepted_commit_title_fingerprint",
        "intercepted_commit_message_fingerprint",
        "message_source_fingerprint",
        "delivered_message_fingerprint",
        "repository_merge_settings_fingerprint",
        "operation_fingerprint",
        "snapshot_fingerprint",
        "attempt",
    }
    if snapshot.mode == "issue-start":
        return {
            "head_oid": None,
            "base_ref_name": None,
            "default_branch": None,
            "merge_method": None,
            "intercepted_commit_title_fingerprint": None,
            "intercepted_commit_message_fingerprint": None,
            "message_source_fingerprint": None,
            "delivered_message_fingerprint": None,
            "repository_merge_settings_fingerprint": None,
            "operation_fingerprint": fingerprint(
                {
                    "mode": snapshot.mode,
                    "repository": snapshot.repository,
                    "number": snapshot.subject_number,
                }
            ),
            "snapshot_fingerprint": fingerprint(_snapshot_graph(snapshot)),
            "attempt": 1,
        }
    if set(snapshot.binding) != keys:
        raise ValueError("PR binding keys mismatch")
    value = dict(snapshot.binding)
    value["snapshot_fingerprint"] = fingerprint(_snapshot_graph(snapshot))
    return value


def _snapshot_graph(snapshot: Snapshot) -> dict[str, Any]:
    return {
        "nodes": {
            ref: {
                "node_id": node.node_id,
                "state": node.state.value,
                "blocked_by": sorted(node.blocked_by),
                "parent": node.parent,
                "children": sorted(node.children),
            }
            for ref, node in sorted(snapshot.nodes.items())
        },
        "roots": list(snapshot.roots),
        "virtual_closed": sorted(snapshot.virtual_closed),
        "pages_complete": snapshot.pages_complete,
    }


def _apply_verified_waivers(
    snapshot: Snapshot,
    findings: list[Finding],
    provider: WaiverProvider | None,
) -> tuple[list[Finding], list[str], bool]:
    """providerのraw mappingを信用せず、parser/verifier通過値だけを適用する。"""
    if provider is None or not any(item.code == "OPEN_BLOCKER" for item in findings):
        return findings, [], False
    try:
        collection = provider.collect_waiver_materials(snapshot.repository)
    except Exception:
        return findings, ["WAIVER_INVALID"], False
    if not isinstance(collection, WaiverCollection):
        return findings, ["WAIVER_INVALID"], False
    errors = list(collection.errors)
    verified: dict[str, list[Mapping[str, str]]] = {}
    now = datetime.now(timezone.utc)
    for material in collection.materials:
        if not isinstance(material, WaiverMaterial):
            errors.append("WAIVER_INVALID")
            continue
        try:
            policy = parse_policy_yaml(material.policy_bytes)
            waiver = parse_waiver_yaml(material.waiver_bytes)
        except WaiverError as exc:
            errors.append(exc.reason)
            continue
        scope = waiver["scope"]
        subject = scope["subject"]
        if (
            waiver["repository"] != snapshot.repository
            or scope["mode"] != snapshot.mode
            or subject["type"] != snapshot.subject_type
            or subject["number"] != snapshot.subject_number
        ):
            continue
        for finding in findings:
            if finding.code != "OPEN_BLOCKER" or finding.fingerprint not in scope["finding_fingerprints"]:
                continue
            try:
                evidence = verify_waiver(
                    waiver,
                    policy,
                    WaiverContext(
                        repository=snapshot.repository,
                        mode=snapshot.mode,
                        subject_type=snapshot.subject_type,
                        subject_number=snapshot.subject_number,
                        finding_fingerprint=finding.fingerprint or "",
                        now=now,
                    ),
                    material.evidence,
                )
            except WaiverError as exc:
                errors.append(exc.reason)
                continue
            verified.setdefault(finding.fingerprint or "", []).append(evidence)

    updated: list[Finding] = []
    applied = False
    for finding in findings:
        candidates = verified.get(finding.fingerprint or "", [])
        if len(candidates) > 1:
            errors.append("WAIVER_INVALID")
            updated.append(finding)
        elif len(candidates) == 1:
            evidence = candidates[0]
            applied = True
            updated.append(
                Finding(
                    finding.code,
                    finding.subject,
                    finding.path,
                    finding.fingerprint,
                    evidence["waiver_id"],
                    evidence,
                )
            )
        else:
            updated.append(finding)
    return updated, sorted(set(errors)), applied


def evaluate_snapshot(
    raw: Mapping[str, Any], waiver_provider: WaiverProvider | None = None
) -> dict[str, Any]:
    """snapshot を全stage評価し、schema/semantic検証済み Result を返す。"""
    try:
        snapshot = parse_snapshot(raw)
        binding = _binding(snapshot)
    except (KeyError, TypeError, ValueError):
        return _contract_error_result(raw, "RESULT_CONTRACT_INVALID")

    findings: list[Finding] = []
    errors = list(snapshot.errors)
    try:
        validate_graph(snapshot.nodes, snapshot.repository)
        if snapshot.mode == "issue-start":
            root_ref = f"{snapshot.repository}#{snapshot.subject_number}"
            root = snapshot.nodes.get(root_ref)
            if root is None:
                errors.append("RELATION_TARGET_UNREADABLE")
            elif root.state is not IssueClass.OPEN:
                findings.append(Finding("TARGET_ISSUE_NOT_OPEN", root_ref, (root_ref,)))
        findings.extend(
            evaluate_dependencies(snapshot.nodes, snapshot.roots, snapshot.virtual_closed)
        )
        findings.extend(
            evaluate_closure_invariant(snapshot.nodes, snapshot.roots, snapshot.virtual_closed)
        )
    except GraphEvaluationError as exc:
        errors.append(exc.reason)
        subject = exc.path[0] if exc.path else f"{snapshot.repository}#{snapshot.subject_number}"
        findings.append(Finding(exc.reason, subject, exc.path or (subject,)))

    finalized = [item.finalized(snapshot.mode) for item in sort_findings(findings)]
    finalized, waiver_errors, applied = _apply_verified_waivers(
        snapshot, finalized, waiver_provider
    )
    errors.extend(waiver_errors)

    errors = sorted(set(errors))
    unwaived_blocks = [item for item in finalized if item.code in BLOCK_REASONS and item.waiver_id is None]
    error_findings = [item for item in finalized if item.code in ERROR_REASONS]
    if errors or error_findings:
        verdict = Verdict.ERROR
        reasons = sorted(set(errors) | {item.code for item in error_findings} | {item.code for item in unwaived_blocks})
        primary = next(reason for reason in reasons if reason in ERROR_REASONS)
        exit_code = 20
    elif unwaived_blocks:
        verdict = Verdict.BLOCK
        reasons = sorted({item.code for item in unwaived_blocks})
        primary = reasons[0]
        exit_code = 10
    else:
        verdict = Verdict.ALLOW
        if applied:
            primary = "WAIVER_APPLIED"
        elif snapshot.mode == "pr-merge" and not snapshot.roots:
            primary = "NO_CLOSING_EFFECT"
        else:
            primary = "NO_VIOLATION"
        reasons = [primary]
        exit_code = 0

    completed_at = _timestamp()
    result = {
        "schema": RESULT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "classifier_version": CLASSIFIER_VERSION,
        "invocation_id": str(uuid4()),
        "mode": snapshot.mode,
        "result": verdict.value,
        "exit_code": exit_code,
        "primary_reason": primary,
        "reasons": reasons,
        "repository": snapshot.repository,
        "subject": {"type": snapshot.subject_type, "number": snapshot.subject_number},
        "binding": binding,
        "graphql_closing_set": list(snapshot.graphql_closing_set),
        "delivered_message_closing_set": list(snapshot.delivered_message_closing_set),
        "closing_set": sorted(set(snapshot.graphql_closing_set) | set(snapshot.delivered_message_closing_set)),
        "findings": [item.to_dict() for item in sort_findings(finalized)],
        "fetched_at": snapshot.fetched_at,
        "completed_at": completed_at,
        "pages_complete": snapshot.pages_complete and not any(reason in INCOMPLETE_REASONS for reason in errors),
        "permit_issued": verdict is Verdict.ALLOW,
    }
    try:
        validate_result_semantics(result, process_exit=exit_code)
    except ContractError:
        trusted_reason = next(
            (reason for reason in errors if reason in ERROR_REASONS),
            "RESULT_CONTRACT_INVALID",
        )
        return _contract_error_result(raw, trusted_reason)
    return result


def _contract_error_result(raw: Mapping[str, Any], reason: str) -> dict[str, Any]:
    now = _timestamp()
    trusted_reason = reason if reason in ERROR_REASONS else "RESULT_CONTRACT_INVALID"
    result = {
        "schema": RESULT_SCHEMA,
        "policy_version": POLICY_VERSION,
        "classifier_version": CLASSIFIER_VERSION,
        "invocation_id": str(uuid4()),
        "mode": "issue-start",
        "result": "ERROR",
        "exit_code": 20,
        "primary_reason": trusted_reason,
        "reasons": [trusted_reason],
        "repository": None,
        "subject": None,
        "binding": {
            "head_oid": None,
            "base_ref_name": None,
            "default_branch": None,
            "merge_method": None,
            "intercepted_commit_title_fingerprint": None,
            "intercepted_commit_message_fingerprint": None,
            "message_source_fingerprint": None,
            "delivered_message_fingerprint": None,
            "repository_merge_settings_fingerprint": None,
            "operation_fingerprint": fingerprint({"invalid_snapshot": True}),
            "snapshot_fingerprint": None,
            "attempt": 1,
        },
        "graphql_closing_set": [],
        "delivered_message_closing_set": [],
        "closing_set": [],
        "findings": [],
        "fetched_at": now,
        "completed_at": now,
        "pages_complete": False,
        "permit_issued": False,
    }
    validate_result_semantics(result, process_exit=20)
    return result


def resolve_issue(
    collector: Collector,
    repository: str,
    number: int,
    waiver_provider: WaiverProvider | None = None,
) -> dict[str, Any]:
    provider = waiver_provider
    if provider is None and hasattr(collector, "collect_waiver_materials"):
        provider = cast(WaiverProvider, collector)
    return evaluate_snapshot(collector.collect_issue(repository, number), provider)


def resolve_pull_request(
    collector: Collector,
    repository: str,
    number: int,
    merge_method: str,
    waiver_provider: WaiverProvider | None = None,
) -> dict[str, Any]:
    provider = waiver_provider
    if provider is None and hasattr(collector, "collect_waiver_materials"):
        provider = cast(WaiverProvider, collector)
    return evaluate_snapshot(
        collector.collect_pull_request(repository, number, merge_method), provider
    )
