"""Collect all repository-owned workflow anomalies into a stable report."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from .diagnostics import collection_error
from .github_api import GitHubAPI
from .pagination import check_run_id, latest_completed_run, pages
from .report_constants import COLLECTOR_PATH, FAILURE_CONCLUSIONS, SCHEMA_VERSION
from .run_interpretation import failure_diagnostic, run_details
from .workflow_collection import collect_workflow

_pages = pages
_check_run_id = check_run_id
_latest_completed_run = latest_completed_run
_collection_error = collection_error


def collect_report(
    get: Callable[[str, dict[str, object] | None], Any],
    repository: str,
    *,
    branch: str = "main",
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Collect each workflow's newest completed run and produce anomaly diagnostics."""
    timestamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    anomalies = []
    workflows_checked = 0
    collection_errors = 0

    def record_run_found():
        nonlocal workflows_checked
        workflows_checked += 1

    workflow_path = f"/repos/{repository}/actions/workflows"
    workflow_pages = iter(pages(get, workflow_path, "workflows"))
    while True:
        try:
            workflow = next(workflow_pages)
        except StopIteration:
            break
        except Exception as error:
            anomalies.append(collection_error(None, "workflow enumeration", error))
            collection_errors += 1
            break
        try:
            result = collect_workflow(
                get, repository, workflow, branch,
                on_run_found=record_run_found,
                diagnostics=anomalies,
            )
        except Exception as error:
            source = workflow if isinstance(workflow, dict) else None
            anomalies.append(collection_error(source, "workflow collection", error))
            collection_errors += 1
    anomalies.sort(
        key=lambda item: (
            0 if item["severity"] == "error" else 1,
            item["workflow"]["name"],
            item["summary"],
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp.isoformat().replace("+00:00", "Z"),
        "repository": repository,
        "branch": branch,
        "workflows_checked": workflows_checked,
        "collection_errors": collection_errors,
        "anomalies": anomalies,
    }


__all__ = [
    "COLLECTOR_PATH", "FAILURE_CONCLUSIONS", "GitHubAPI", "SCHEMA_VERSION",
    "check_run_id", "collect_report", "latest_completed_run", "pages",
    "run_details", "failure_diagnostic",
]
