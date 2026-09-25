"""全 workflow の main 最新 run から失敗と warning annotation を集約する。

workflow 名の allowlist は持たない。GitHub Actions API から workflow を列挙し、
各 workflow の ``main`` における最新の完了 run を読む。これにより、新しい workflow
が追加されても collector の更新なしで対象になる。
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

SCHEMA_VERSION = 1
COLLECTOR_PATH = ".github/workflows/ci-anomaly-report.yml"
FAILURE_CONCLUSIONS = {
    "action_required",
    "failure",
    "stale",
    "startup_failure",
    "timed_out",
}


class GitHubAPI:
    """この collector が必要とする read-only REST API の薄い wrapper。"""

    def __init__(self, token: str, *, api_url: str = "https://api.github.com"):
        self.token = token
        self.api_url = api_url.rstrip("/")

    def get(self, path_or_url: str, params: dict[str, object] | None = None) -> Any:
        url = path_or_url if path_or_url.startswith("http") else self.api_url + path_or_url
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "review-system-ci-anomaly-report",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)


def _pages(
    get: Callable[[str, dict[str, object] | None], Any],
    path: str,
    key: str | None,
    params: dict[str, object] | None = None,
) -> Iterable[dict[str, Any]]:
    """REST collection を空ページまで列挙する（100件上限での黙った欠落を防ぐ）。"""

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


def _check_run_id(job: dict[str, Any]) -> int:
    url = str(job.get("check_run_url") or "")
    try:
        return int(url.rstrip("/").rsplit("/", 1)[-1])
    except (TypeError, ValueError):
        # GitHub Actions の job id と check run id は現在同値だが、URL を正本にする。
        # URL 欠落時だけ documented job id へ倒す。
        return int(job["id"])


def _latest_completed_run(
    get: Callable[[str, dict[str, object] | None], Any],
    repository: str,
    workflow_id: int,
    branch: str,
) -> dict[str, Any] | None:
    payload = get(
        f"/repos/{repository}/actions/workflows/{workflow_id}/runs",
        {"branch": branch, "status": "completed", "per_page": 1},
    )
    runs = payload.get("workflow_runs", [])
    if not isinstance(runs, list):
        raise ValueError("GitHub API workflow_runs is not a list")
    return runs[0] if runs else None


def _collection_error(
    workflow: dict[str, Any] | None,
    stage: str,
    error: Exception,
) -> dict[str, Any]:
    """API/response failureをreport内の非信頼診断データへ変換する。"""

    source = workflow or {}
    workflow_id = source.get("id", 0)
    return {
        "workflow": {
            "id": workflow_id,
            "name": str(source.get("name") or "CI anomaly collector"),
            "path": str(source.get("path") or COLLECTOR_PATH),
        },
        "severity": "error",
        "kind": "collection_error",
        # Exception本文にはURL等の外部入力が入り得るため、型名だけを公開する。
        "summary": f"collection failed during {stage} ({type(error).__name__})",
        "details_url": "",
    }


def collect_report(
    get: Callable[[str, dict[str, object] | None], Any],
    repository: str,
    *,
    branch: str = "main",
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """対象 branch の workflow ごとの最新完了 run を異常レポートへ変換する。"""

    timestamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    anomalies: list[dict[str, Any]] = []
    workflows_checked = 0
    collection_errors = 0

    workflow_path = f"/repos/{repository}/actions/workflows"
    workflow_pages = iter(_pages(get, workflow_path, "workflows"))
    while True:
        try:
            workflow = next(workflow_pages)
        except StopIteration:
            break
        except Exception as error:
            anomalies.append(_collection_error(None, "workflow enumeration", error))
            collection_errors += 1
            break

        try:
            if not isinstance(workflow, dict):
                raise TypeError("GitHub API workflow item is not an object")
            path = str(workflow.get("path") or "")
            # Repository-owned workflow filesだけがオーナー確定スコープ。GitHub API は
            # Copilot/Claude の dynamic workflow も返すため、明示的に境界を固定する。
            if not path.startswith(".github/workflows/"):
                continue
            workflow_id = int(workflow["id"])
            run = _latest_completed_run(get, repository, workflow_id, branch)
            if run is None:
                continue
            workflows_checked += 1
            workflow_info = {
                "id": workflow_id,
                "name": str(workflow.get("name") or run.get("name") or workflow_id),
                "path": path,
            }
            run_info = {
                "id": int(run["id"]),
                "attempt": int(run.get("run_attempt") or 1),
                "conclusion": str(run.get("conclusion") or "unknown"),
                "event": str(run.get("event") or "unknown"),
                "head_sha": str(run.get("head_sha") or ""),
                "completed_at": run.get("updated_at") or run.get("created_at"),
            }
            details_url = str(run.get("html_url") or "")

            if run_info["conclusion"] in FAILURE_CONCLUSIONS:
                anomalies.append(
                    {
                        "workflow": workflow_info,
                        "severity": "error",
                        "summary": (
                            f"workflow run concluded {run_info['conclusion']} on {branch}"
                        ),
                        "details_url": details_url,
                        "run": run_info,
                    }
                )

            jobs_path = f"/repos/{repository}/actions/runs/{run_info['id']}/jobs"
            for job in _pages(get, jobs_path, "jobs"):
                check_id = _check_run_id(job)
                annotations_path = (
                    f"/repos/{repository}/check-runs/{check_id}/annotations"
                )
                for annotation in _pages(get, annotations_path, None):
                    if annotation.get("annotation_level") != "warning":
                        continue
                    title = str(annotation.get("title") or "GitHub Actions warning")
                    message = " ".join(str(annotation.get("message") or "").split())
                    location = str(annotation.get("path") or "")
                    if annotation.get("start_line"):
                        location += f":{annotation['start_line']}"
                    anomalies.append(
                        {
                            "workflow": workflow_info,
                            "severity": "warning",
                            "summary": f"{title}: {message}".strip(),
                            "details_url": str(job.get("html_url") or details_url),
                            "run": run_info,
                            "job": str(job.get("name") or job.get("id") or "unknown"),
                            "location": location,
                        }
                    )
        except Exception as error:
            source = workflow if isinstance(workflow, dict) else None
            anomalies.append(_collection_error(source, "workflow collection", error))
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
