"""Read item-scoped GitHub evidence for issue histories, relationships and PR checks."""

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, NamedTuple
from urllib.parse import urlencode

from . import records
from .gh_issue_transitions import candidates, transition
from .gh_pull_records import changed_file
from .github import evidence, get

PAGE_SIZE = 100


class Detail(NamedTuple):
    kind: str
    key: int | str
    endpoint: str
    convert: Callable[[dict], dict]
    collection: str | None = None


def path(endpoint, **query):
    return endpoint + "?" + urlencode({"per_page": PAGE_SIZE, **query})


def details(repository, issues, pulls, period, max_pages):
    sources = {key: {} for key in ("blocked_by", "sub_issues", "reviews", "head_ci", "issue_events", "pull_files")}
    requests = [*_issue_requests(repository, issues, period, sources), *_pull_requests(pulls, period)]
    with ThreadPoolExecutor(max_workers=6) as workers:
        results = workers.map(lambda item: _get(repository, max_pages, item), requests)
        for request, result in zip(requests, results):
            sources[request.kind][request.key] = result
    return sources


def _get(repository, max_pages, request):
    return get(repository, request.endpoint, max_pages, convert=request.convert, collection=request.collection)


def _issue_requests(repository, issues, period, sources):
    for issue in candidates(issues, period):
        number = issue["number"]
        yield Detail("issue_events", number, path(f"issues/{number}/events"), transition)
    for issue in issues:
        number = issue["number"]
        if issue["state"] == "open":
            summary = issue["dependencies_summary"]
            total = summary.get("total_blocked_by") if summary else None
            if type(total) is int and total == 0:
                source = f"https://api.github.com/repos/{repository}/issues"
                sources["blocked_by"][number] = evidence(source, [], retrieved_total=0,
                                                         summary_field="issue_dependencies_summary.total_blocked_by")
            else:
                yield Detail("blocked_by", number, path(f"issues/{number}/dependencies/blocked_by"), records.relation)
        children = issue["sub_issues_summary"]
        if children and children.get("total"):
            yield Detail("sub_issues", number, path(f"issues/{number}/sub_issues"), records.relation)


def _pull_requests(pulls, period):
    seen = set()
    for pull in pulls:
        if not review_target(pull, period):
            continue
        number, head = pull["number"], pull["head_sha"]
        yield Detail("reviews", number, path(f"pulls/{number}/reviews"), records.review)
        if pull["state"] == "open":
            yield Detail("pull_files", number, path(f"pulls/{number}/files"), changed_file)
        if head is not None and head not in seen:
            seen.add(head)
            endpoint = path("actions/runs", head_sha=head, event="pull_request")
            yield Detail("head_ci", head, endpoint, records.workflow_run, "workflow_runs")


def review_target(pull, period):
    return pull["state"] == "open" or period.contains(pull["closed_at"]) or period.contains(pull["merged_at"])
