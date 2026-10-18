"""Interpret workflow run metadata as report fields and failure diagnostics."""

from __future__ import annotations

from typing import Any

from .report_constants import FAILURE_CONCLUSIONS


def run_details(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(run["id"]),
        "attempt": int(run.get("run_attempt") or 1),
        "conclusion": str(run.get("conclusion") or "unknown"),
        "event": str(run.get("event") or "unknown"),
        "head_sha": str(run.get("head_sha") or ""),
        "completed_at": run.get("updated_at") or run.get("created_at"),
    }


def failure_diagnostic(workflow_info, run_info, branch: str, details_url: str):
    if run_info["conclusion"] not in FAILURE_CONCLUSIONS:
        return None
    return {
        "workflow": workflow_info,
        "severity": "error",
        "summary": f"workflow run concluded {run_info['conclusion']} on {branch}",
        "details_url": details_url,
        "run": run_info,
    }
