"""PR merge blocker gate のfresh評価と直前再束縛。"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from blocker_gate.contract import ContractError, validate_result_semantics
from blocker_gate.github import GitHubCollector
from blocker_gate.resolver import evaluate_snapshot

from .classifier import MergeOperation


PR_MERGE_POLICY_VERSION = "1.0"


class PrMergeGateError(RuntimeError):
    """gate評価を安全に継続できない。"""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def _collect(collector: Any, operation: MergeOperation, attempt: int) -> dict[str, Any]:
    raw = collector.collect_pull_request(
        operation.repository,
        operation.pr_number,
        operation.merge_method,
        commit_title=operation.commit_title,
        commit_message=operation.commit_message,
        expected_head_oid=operation.expected_head_oid,
        operation_fingerprint=operation.operation_fingerprint,
        attempt=attempt,
    )
    result = evaluate_snapshot(raw, waiver_provider=None)
    validate_result_semantics(result, int(result["exit_code"]))
    subject = result.get("subject")
    binding = result.get("binding")
    if (
        result.get("mode") != "pr-merge"
        or result.get("repository") != operation.repository
        or not isinstance(subject, dict)
        or subject.get("type") != "pull_request"
        or subject.get("number") != operation.pr_number
        or not isinstance(binding, dict)
        or binding.get("merge_method") != operation.merge_method
        or binding.get("operation_fingerprint") != operation.operation_fingerprint
        or binding.get("attempt") != attempt
    ):
        raise PrMergeGateError("IDENTITY_MISMATCH")
    if operation.expected_head_oid is not None and binding.get("head_oid") != operation.expected_head_oid:
        raise PrMergeGateError("IDENTITY_MISMATCH")
    return result


def _stable_material(result: Mapping[str, Any]) -> dict[str, Any]:
    binding = dict(result["binding"])
    binding.pop("attempt", None)
    return {
        "repository": result["repository"],
        "subject": result["subject"],
        "result": result["result"],
        "primary_reason": result["primary_reason"],
        "reasons": result["reasons"],
        "binding": binding,
        "graphql_closing_set": result["graphql_closing_set"],
        "delivered_message_closing_set": result["delivered_message_closing_set"],
        "closing_set": result["closing_set"],
        "findings": result["findings"],
        "pages_complete": result["pages_complete"],
    }


def _reevaluation_error(result: Mapping[str, Any]) -> dict[str, Any]:
    failed = deepcopy(dict(result))
    failed.update(
        {
            "result": "ERROR",
            "exit_code": 20,
            "primary_reason": "REEVALUATION_LIMIT",
            "reasons": ["REEVALUATION_LIMIT"],
            "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "permit_issued": False,
        }
    )
    validate_result_semantics(failed, 20)
    return failed


def _evidence(operation: MergeOperation, result: Mapping[str, Any]) -> dict[str, Any]:
    allowed = result["result"] == "ALLOW" and result["permit_issued"] is True
    return {
        "schema_version": "pr-merge-evidence/1",
        "policy_version": PR_MERGE_POLICY_VERSION,
        "result": result["result"],
        "exit_code": result["exit_code"],
        "reason": result["primary_reason"],
        "fetched_at": result["fetched_at"],
        "binding": {
            "repository": operation.repository,
            "pr_number": operation.pr_number,
            "merge_method": operation.merge_method,
            "transport": operation.transport,
            "operation_fingerprint": operation.operation_fingerprint,
        },
        "blocker_evidence": dict(result),
        "permit_issued": allowed,
        "merge_api_called": False,
        "next_action": "CONTINUE_ORIGINAL_ONCE" if allowed else "DO_NOT_MERGE",
    }


def evaluate_merge_operation(
    operation: MergeOperation,
    *,
    collector_factory: Callable[[str | None], Any] = GitHubCollector,
    token: str | None = None,
) -> dict[str, Any]:
    """最大3attemptでfresh評価と同一snapshotの直前再読を行う。"""
    try:
        collector = collector_factory(token)
        latest: dict[str, Any] | None = None
        for attempt in range(1, 4):
            evaluated = _collect(collector, operation, attempt)
            latest = evaluated
            if evaluated["result"] != "ALLOW":
                return _evidence(operation, evaluated)
            rebound = _collect(collector, operation, attempt)
            latest = rebound
            if rebound["result"] != "ALLOW":
                return _evidence(operation, rebound)
            if _stable_material(evaluated) == _stable_material(rebound):
                return _evidence(operation, rebound)
        assert latest is not None
        return _evidence(operation, _reevaluation_error(latest))
    except PrMergeGateError:
        raise
    except ContractError as exc:
        raise PrMergeGateError("RESULT_CONTRACT_INVALID", str(exc)) from exc
    except Exception as exc:
        raise PrMergeGateError("INTERNAL_ERROR", type(exc).__name__) from exc


def fail_closed(
    classification_fingerprint: str,
    reason: str,
    operation: MergeOperation | None = None,
) -> dict[str, Any]:
    """classifier/runtime失敗をmerge permitへ変換せずhook evidenceにする。"""
    return {
        "schema_version": "pr-merge-evidence/1",
        "policy_version": PR_MERGE_POLICY_VERSION,
        "result": "BLOCK" if reason == "AUTO_MERGE_DENIED" else "ERROR",
        "exit_code": 10 if reason == "AUTO_MERGE_DENIED" else 20,
        "reason": reason,
        "fetched_at": None,
        "binding": {
            "repository": operation.repository if operation else None,
            "pr_number": operation.pr_number if operation else None,
            "merge_method": operation.merge_method if operation else None,
            "transport": operation.transport if operation else None,
            "operation_fingerprint": classification_fingerprint,
        },
        "blocker_evidence": None,
        "permit_issued": False,
        "merge_api_called": False,
        "next_action": "DO_NOT_MERGE",
    }
