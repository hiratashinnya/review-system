"""Fresh PR blocker reevaluation for the owner report command."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from blocker_gate.contract import ContractError, validate_result_semantics
from blocker_gate.github import GitHubCollector
from blocker_gate.resolver import evaluate_snapshot

from .audit import build_owner_report


class PrMergeGateError(RuntimeError):
    """Report evaluation could not safely continue."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _collect(collector: Any, repository: str, number: int, method: str, attempt: int) -> dict[str, Any]:
    raw = collector.collect_pull_request(repository, number, method, attempt=attempt)
    result = evaluate_snapshot(raw, waiver_provider=None)
    validate_result_semantics(result, int(result["exit_code"]))
    subject, binding = result.get("subject"), result.get("binding")
    if (
        result.get("mode") != "pr-merge"
        or result.get("repository") != repository
        or not isinstance(subject, dict)
        or subject.get("type") != "pull_request"
        or subject.get("number") != number
        or not isinstance(binding, dict)
        or binding.get("merge_method") != method
        or binding.get("attempt") != attempt
    ):
        raise PrMergeGateError("IDENTITY_MISMATCH")
    return result


def _stable_material(result: Mapping[str, Any]) -> dict[str, Any]:
    binding = dict(result["binding"])
    binding.pop("attempt", None)
    keys = ("graphql_closing_set", "delivered_message_closing_set", "closing_set",
            "findings", "pages_complete")
    return {
        "repository": result["repository"], "subject": result["subject"],
        "result": result["result"], "primary_reason": result["primary_reason"],
        "reasons": result["reasons"], "binding": binding,
        **{key: result[key] for key in keys},
    }


def _unstable_result(result: Mapping[str, Any]) -> dict[str, Any]:
    failed = deepcopy(dict(result))
    failed.update(result="ERROR", exit_code=20, primary_reason="REEVALUATION_LIMIT",
                  reasons=["REEVALUATION_LIMIT"],
                  completed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                  permit_issued=False)
    validate_result_semantics(failed, 20)
    return failed


def evaluate_owner_report(
    repository: str, number: int, method: str, *,
    collector_factory: Callable[[str | None], Any] = GitHubCollector,
    token: str | None = None,
) -> dict[str, Any]:
    """Return a stable blocker report without authorizing or performing a merge."""
    if not repository or "/" not in repository or any(c.isspace() for c in repository):
        raise ValueError("repository must be OWNER/REPO")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ValueError("pull request number must be positive")
    if method not in {"merge", "rebase", "squash"}:
        raise ValueError("unsupported merge method")
    try:
        collector = collector_factory(token)
        latest: dict[str, Any] | None = None
        for attempt in range(1, 4):
            checked = _collect(collector, repository, number, method, attempt)
            latest = checked
            if checked["result"] != "ALLOW":
                break
            rebound = _collect(collector, repository, number, method, attempt)
            latest = rebound
            if rebound["result"] != "ALLOW":
                break
            if _stable_material(checked) == _stable_material(rebound):
                break
        else:
            latest = _unstable_result(latest)
        return build_owner_report(repository, number, method, latest)
    except PrMergeGateError:
        raise
    except ContractError as exc:
        raise PrMergeGateError("RESULT_CONTRACT_INVALID") from exc
    except Exception as exc:
        raise PrMergeGateError("INTERNAL_ERROR") from exc
