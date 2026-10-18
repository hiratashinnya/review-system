"""GitHub REST collection pagination and latest-run lookup."""

from __future__ import annotations

from typing import Any, Callable, Iterable


def pages(
    get: Callable[[str, dict[str, object] | None], Any],
    path: str,
    key: str | None,
    params: dict[str, object] | None = None,
) -> Iterable[dict[str, Any]]:
    """Yield collection pages until exhausted, avoiding silent 100-item truncation."""
    page = 1
    while True:
        query = dict(params or {})
        query.update({"per_page": 100, "page": page})
        payload = get(path, query)
        items = payload.get(key, []) if key else payload
        if not isinstance(items, list):
            raise ValueError(f"GitHub API response for {path} has no list {key!r}")
        yield from items
        if len(items) < 100:
            return
        page += 1


def check_run_id(job: dict[str, Any]) -> int:
    url = str(job.get("check_run_url") or "")
    try:
        return int(url.rstrip("/").rsplit("/", 1)[-1])
    except (TypeError, ValueError):
        # The documented job id fallback applies only when check_run_url is absent/invalid.
        return int(job["id"])


def latest_completed_run(get, repository: str, workflow_id: int, branch: str):
    payload = get(
        f"/repos/{repository}/actions/workflows/{workflow_id}/runs",
        {"branch": branch, "status": "completed", "per_page": 1},
    )
    runs = payload.get("workflow_runs", [])
    if not isinstance(runs, list):
        raise ValueError("GitHub API workflow_runs is not a list")
    return runs[0] if runs else None
