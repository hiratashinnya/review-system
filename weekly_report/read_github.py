"""Collect repository activity and per-item evidence from GitHub."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlencode

from . import records
from .github import evidence, get

PAGE_SIZE = 100


def collect(repository, period, max_pages):
    issues = get(repository, path("issues", state="all", sort="created", direction="asc"),
                 max_pages, convert=records.issue)
    if issues["rows"] is not None:
        issues["rows"] = [row for row in issues["rows"] if not row["is_pull"]]
    pulls = get(repository, path("pulls", state="all", sort="created", direction="asc"),
                max_pages, convert=records.pull)
    ci = read_ci(repository, period, max_pages)
    tasks = _detail_tasks(issues["rows"] or [], pulls["rows"] or [], period)
    with ThreadPoolExecutor(max_workers=6) as workers:
        details = workers.map(
            lambda task: get(repository, path(task[2]), max_pages, convert=task[3]), tasks,
        )
        by_kind = {"blocked_by": {}, "sub_issues": {}, "reviews": {}}
        for (kind, number, _, _), detail in zip(tasks, details):
            by_kind[kind][number] = detail
    return {"issues": issues, "pulls": pulls, "ci": ci, **by_kind}


def path(endpoint, **query):
    return endpoint + "?" + urlencode({"per_page": PAGE_SIZE, **query})


def read_ci(repository, period, max_pages):
    source = f"https://api.github.com/repos/{repository}/actions/runs"
    shards, runs = [], []
    start = period.start
    while start < period.cutoff:
        end = min(start + timedelta(days=1), period.cutoff)
        query = path("actions/runs", created=f"{start.isoformat()}..{end.isoformat()}")
        result = get(repository, query, max_pages, collection="workflow_runs", convert=records.workflow_run)
        metadata = {key: value for key, value in result.items() if key != "rows"}
        shards.append(metadata)
        if result["rows"] is not None:
            runs.extend(row for row in result["rows"] if start <= row["created_at"] < end)
        start = end
    if any(shard["reason"] for shard in shards):
        return evidence(source, reason="CI の日別取得に欠損があります", shards=shards)
    if len({row["id"] for row in runs}) != len(runs):
        return evidence(source, reason="CI の日別取得に重複があります", shards=shards)
    return evidence(source, runs, retrieved_total=len(runs), shards=shards)


def _detail_tasks(issues, pulls, period):
    tasks = []
    for issue in issues:
        number = issue["number"]
        summary = issue["sub_issues_summary"]
        if issue["state"] == "open":
            tasks.append(("blocked_by", number, f"issues/{number}/dependencies/blocked_by", records.relation))
        if (summary and summary.get("total")) and (
            issue["state"] == "open" or period.contains(issue["closed_at"])
        ):
            tasks.append(("sub_issues", number, f"issues/{number}/sub_issues", records.relation))
    for pull in pulls:
        number = pull["number"]
        if (pull["state"] == "open" or period.contains(pull["closed_at"])
                or period.contains(pull["merged_at"])):
            tasks.append(("reviews", number, f"pulls/{number}/reviews", records.review))
    return tasks
