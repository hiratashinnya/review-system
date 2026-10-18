"""Collection failure and warning annotation diagnostic construction."""

from __future__ import annotations

from typing import Any

from .report_constants import COLLECTOR_PATH


def collection_error(workflow: dict[str, Any] | None, stage: str, error: Exception):
    """Convert API/response failure into untrusted diagnostic data in the report."""
    source = workflow or {}
    return {
        "workflow": {
            "id": source.get("id", 0),
            "name": str(source.get("name") or "CI anomaly collector"),
            "path": str(source.get("path") or COLLECTOR_PATH),
        },
        "severity": "error",
        "kind": "collection_error",
        "summary": f"collection failed during {stage} ({type(error).__name__})",
        "details_url": "",
    }


def warning_diagnostic(annotation, job, workflow_info, run_info, details_url):
    if annotation.get("annotation_level") != "warning":
        return None
    title = str(annotation.get("title") or "GitHub Actions warning")
    message = " ".join(str(annotation.get("message") or "").split())
    location = str(annotation.get("path") or "")
    if annotation.get("start_line"):
        location += f":{annotation['start_line']}"
    return {
        "workflow": workflow_info,
        "severity": "warning",
        "summary": f"{title}: {message}".strip(),
        "details_url": str(job.get("html_url") or details_url),
        "run": run_info,
        "job": str(job.get("name") or job.get("id") or "unknown"),
        "location": location,
    }
