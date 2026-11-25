"""Collect repository activity and per-item evidence from GitHub."""

from datetime import timedelta

from . import records
from .gh_consistency import compare_reads
from .gh_details import details, path
from .gh_issue_transitions import transition_evidence
from .gh_pull_files import verify_file_sets
from .github import evidence, get

def collect(repository, period, max_pages):
    issues = _issues(repository, max_pages)
    pulls = _pulls(repository, max_pages)
    ci = read_ci(repository, period, max_pages)
    per_item = details(repository, issues["rows"] or [], pulls["rows"] or [], period, max_pages)
    consistency = {
        "issues": compare_reads(issues, _issues(repository, max_pages)),
        "pulls": compare_reads(pulls, _pulls(repository, max_pages)),
    }
    transitions = transition_evidence(repository, issues, per_item.pop("issue_events"), period, consistency["issues"])
    per_item["pull_files"] = verify_file_sets(per_item["pull_files"], pulls["rows"] or [], consistency["pulls"])
    return {"issues": issues, "pulls": pulls, "ci": ci, **per_item, "transitions": transitions,
            "consistency": consistency}


def _issues(repository, max_pages):
    result = get(repository, path("issues", state="all", sort="created", direction="asc"),
                 max_pages, convert=records.issue)
    if result["rows"] is not None:
        result["rows"] = [row for row in result["rows"] if not row["is_pull"]]
    return result


def _pulls(repository, max_pages):
    return get(repository, path("pulls", state="all", sort="created", direction="asc"),
               max_pages, convert=records.pull)


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
