"""Collect and interpret one repository-owned workflow's latest completed run."""

from __future__ import annotations

from typing import Any, Callable

from .diagnostics import warning_diagnostic
from .pagination import check_run_id, latest_completed_run, pages
from .run_interpretation import failure_diagnostic, run_details


def collect_workflow(
    get: Callable, repository: str, workflow: dict[str, Any], branch: str,
    on_run_found: Callable[[], None], diagnostics: list[dict[str, Any]],
):
    if not isinstance(workflow, dict):
        raise TypeError("GitHub API workflow item is not an object")
    path = str(workflow.get("path") or "")
    if not path.startswith(".github/workflows/"):
        return
    workflow_id = int(workflow["id"])
    run = latest_completed_run(get, repository, workflow_id, branch)
    if run is None:
        return
    on_run_found()

    workflow_info = {
        "id": workflow_id,
        "name": str(workflow.get("name") or run.get("name") or workflow_id),
        "path": path,
    }
    run_info = run_details(run)
    details_url = str(run.get("html_url") or "")
    failure = failure_diagnostic(workflow_info, run_info, branch, details_url)
    if failure:
        diagnostics.append(failure)

    jobs_path = f"/repos/{repository}/actions/runs/{run_info['id']}/jobs"
    for job in pages(get, jobs_path, "jobs"):
        annotations_path = f"/repos/{repository}/check-runs/{check_run_id(job)}/annotations"
        for annotation in pages(get, annotations_path, None):
            diagnostic = warning_diagnostic(
                annotation, job, workflow_info, run_info, details_url
            )
            if diagnostic:
                diagnostics.append(diagnostic)
