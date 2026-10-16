from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping

from blocker_gate.contract import ContractError, validate_result_semantics
from blocker_gate.resolver import evaluate_snapshot
from blocker_gate.snapshot import RepositorySnapshotError, project_issue_snapshot
from .gate_collectors import IssueStartGitHubCollector, SnapshotIssueMetadata
from .gate_evidence import _error_evidence, _result_evidence
from .gate_support import (
    ISSUE_START_POLICY_VERSION, SNAPSHOT_FALLBACK_REASON, IssueStartError, IssueStartRequest,
)
from .gate_snapshot_policy import _assert_snapshot_fresh, _snapshot_fallback_required
from .gate_snapshot_read import read_repository_snapshot
def evaluate_issue_start(
    request: IssueStartRequest,
    *,
    collector_factory: Callable[[str | None], Any] = IssueStartGitHubCollector,
    token: str | None = None,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    now: datetime | None = None,
    snapshot_reader: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Read fresh blockers and evaluate an optional repository snapshot fallback."""
    try:
        collector = collector_factory(token)
        # #299 完了前は waiver provider を渡さない。collector に機能があっても bypass 不可。
        collected = collector.collect_issue(request.repository, request.issue)
        blocker = evaluate_snapshot(collected, waiver_provider=None)
        source = "api"
        snapshot_generated_at: str | None = None
        report_provider: Any = collector
        if _snapshot_fallback_required(blocker, collected):
            read = read_repository_snapshot if snapshot_reader is None else snapshot_reader
            repository_snapshot = read(
                repository=request.repository, cwd=cwd, runner=runner
            )
            _assert_snapshot_fresh(repository_snapshot, now)
            try:
                projected, metadata = project_issue_snapshot(
                    repository_snapshot, request.repository, request.issue
                )
            except RepositorySnapshotError as exc:
                raise IssueStartError(
                    "ISSUE_START_SNAPSHOT_BINDING_MISMATCH", exc.detail or exc.reason
                ) from exc
            # 判定は API 経路と同一の evaluator を通す（ロジックを分岐させない）。
            blocker = evaluate_snapshot(projected, waiver_provider=None)
            source = "snapshot"
            snapshot_generated_at = repository_snapshot["generated_at"]
            report_provider = SnapshotIssueMetadata(metadata)
        validate_result_semantics(blocker, int(blocker["exit_code"]))
        subject = blocker.get("subject")
        if (
            blocker.get("mode") != "issue-start"
            or blocker.get("repository") != request.repository
            or not isinstance(subject, dict)
            or subject.get("type") != "issue"
            or subject.get("number") != request.issue
        ):
            raise IssueStartError("ISSUE_START_BLOCKER_BINDING_MISMATCH")
        return _result_evidence(
            request,
            blocker,
            source=source,
            snapshot_generated_at=snapshot_generated_at,
            report_provider=report_provider,
        )
    except IssueStartError:
        raise
    except ContractError as exc:
        raise IssueStartError("ISSUE_START_CONTRACT_ERROR", str(exc)) from exc
    except RepositorySnapshotError as exc:
        raise IssueStartError("ISSUE_START_SNAPSHOT_INVALID", exc.reason) from exc
    except Exception as exc:
        raise IssueStartError("ISSUE_START_EVALUATION_ERROR", type(exc).__name__) from exc
