"""GitHub 標準 API の read-only collector。"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .model import POLICY_VERSION, SNAPSHOT_SCHEMA, fingerprint

API_VERSION = "2026-03-10"
_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


class GitHubReadError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ReadTransport(Protocol):
    def get(self, url: str, headers: Mapping[str, str]) -> tuple[int, Mapping[str, str], bytes]: ...
    def post(self, url: str, headers: Mapping[str, str], body: bytes) -> tuple[int, Mapping[str, str], bytes]: ...


class UrlLibReadTransport:
    """HTTP GET/POST only。GitHub resource を変更するメソッドを公開しない。"""

    def get(self, url: str, headers: Mapping[str, str]) -> tuple[int, Mapping[str, str], bytes]:
        return self._open(Request(url, headers=dict(headers), method="GET"))

    def post(self, url: str, headers: Mapping[str, str], body: bytes) -> tuple[int, Mapping[str, str], bytes]:
        request = Request(url, data=body, headers=dict(headers), method="POST")
        return self._open(request)

    @staticmethod
    def _open(request: Request) -> tuple[int, Mapping[str, str], bytes]:
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub URLs
                return response.status, dict(response.headers.items()), response.read()
        except HTTPError as exc:
            return exc.code, dict(exc.headers.items()), exc.read()
        except (TimeoutError, URLError) as exc:
            raise GitHubReadError("API_UNAVAILABLE") from exc


class GitHubCollector:
    def __init__(self, token: str | None, transport: ReadTransport | None = None) -> None:
        self._transport = transport or UrlLibReadTransport()
        self._headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "review-system-blocker-gate/1.0",
        }
        if token:
            self._headers["Authorization"] = "Bearer " + token

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def _decode(self, status: int, body: bytes) -> Any:
        if status in {401, 403}:
            raise GitHubReadError("API_PERMISSION")
        if status in {404, 410}:
            raise GitHubReadError("RELATION_TARGET_UNREADABLE")
        if status == 429 or status >= 500:
            raise GitHubReadError("API_UNAVAILABLE")
        if not 200 <= status < 300:
            raise GitHubReadError("API_UNAVAILABLE")
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GitHubReadError("API_PARTIAL_RESPONSE") from exc

    def _get(self, path_or_url: str) -> tuple[Any, Mapping[str, str]]:
        url = path_or_url if path_or_url.startswith("https://") else "https://api.github.com" + path_or_url
        status, headers, body = self._transport.get(url, self._headers)
        return self._decode(status, body), headers

    def _list(self, path: str) -> list[Mapping[str, Any]]:
        separator = "&" if "?" in path else "?"
        next_url: str | None = path + separator + "per_page=100"
        seen: set[str] = set()
        result: list[Mapping[str, Any]] = []
        while next_url is not None:
            if next_url in seen:
                raise GitHubReadError("PAGINATION_INCOMPLETE")
            seen.add(next_url)
            value, headers = self._get(next_url)
            if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            result.extend(value)
            link = next((v for k, v in headers.items() if k.lower() == "link"), "")
            match = _NEXT.search(link)
            next_url = match.group(1) if match else None
        return result

    @staticmethod
    def _ref(repository: str, raw: Mapping[str, Any]) -> str:
        number = raw.get("number")
        if not isinstance(number, int) or number < 1:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        repo_url = raw.get("repository_url")
        if isinstance(repo_url, str):
            actual = "/".join(repo_url.rstrip("/").split("/")[-2:])
            if actual != repository:
                raise GitHubReadError("CROSS_REPOSITORY_UNSUPPORTED")
        return f"{repository}#{number}"

    @staticmethod
    def _state(raw: Mapping[str, Any]) -> str:
        state = raw.get("state")
        reason = raw.get("state_reason")
        if state == "open":
            return "OPEN"
        if state == "closed" and reason == "completed":
            return "CLOSED_COMPLETED"
        if state == "closed" and reason == "not_planned":
            return "CLOSED_NOT_PLANNED"
        return "UNKNOWN"

    def _collect_graph(self, repository: str, roots: list[str]) -> tuple[dict[str, Any], list[str], bool]:
        nodes: dict[str, Any] = {}
        pending = list(roots)
        errors: list[str] = []
        complete = True
        while pending:
            ref = pending.pop()
            if ref in nodes:
                continue
            try:
                number = int(ref.rsplit("#", 1)[1])
                issue, _ = self._get(f"/repos/{repository}/issues/{number}")
                if not isinstance(issue, dict) or "pull_request" in issue:
                    raise GitHubReadError("TARGET_AMBIGUOUS")
                if self._ref(repository, issue) != ref or not isinstance(issue.get("node_id"), str):
                    raise GitHubReadError("IDENTITY_MISMATCH")
                blocked_raw = self._list(f"/repos/{repository}/issues/{number}/dependencies/blocked_by")
                children_raw = self._list(f"/repos/{repository}/issues/{number}/sub_issues")
                blocked = sorted(self._ref(repository, item) for item in blocked_raw)
                children = sorted(self._ref(repository, item) for item in children_raw)
                parent: str | None = None
                if issue.get("parent_issue_url") is not None:
                    parent_raw, _ = self._get(f"/repos/{repository}/issues/{number}/parent")
                    if not isinstance(parent_raw, dict):
                        raise GitHubReadError("API_PARTIAL_RESPONSE")
                    parent = self._ref(repository, parent_raw)
                nodes[ref] = {
                    "node_id": issue["node_id"],
                    "state": self._state(issue),
                    "blocked_by": blocked,
                    "parent": parent,
                    "children": children,
                }
                pending.extend(blocked)
                pending.extend(children)
                if parent is not None:
                    pending.append(parent)
                if len(nodes) + len(set(pending)) > 10_000:
                    raise GitHubReadError("GRAPH_LIMIT_EXCEEDED")
            except GitHubReadError as exc:
                errors.append(exc.reason)
                complete = False
        return nodes, sorted(set(errors)), complete

    def collect_issue(self, repository: str, number: int) -> Mapping[str, Any]:
        root = f"{repository}#{number}"
        nodes, errors, complete = self._collect_graph(repository, [root])
        return {
            "schema": SNAPSHOT_SCHEMA,
            "policy_version": POLICY_VERSION,
            "mode": "issue-start",
            "repository": repository,
            "subject": {"type": "issue", "number": number},
            "roots": [root],
            "virtual_closed": [],
            "nodes": nodes,
            "pages_complete": complete,
            "errors": errors,
            "fetched_at": self._now(),
            "graphql_closing_set": [],
            "delivered_message_closing_set": [],
            "binding": {},
        }

    def _graphql(self, query: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        headers = dict(self._headers)
        headers["Content-Type"] = "application/json"
        body = json.dumps({"query": query, "variables": variables}, separators=(",", ":")).encode("utf-8")
        status, _, raw = self._transport.post("https://api.github.com/graphql", headers, body)
        value = self._decode(status, raw)
        if not isinstance(value, dict) or value.get("errors") or not isinstance(value.get("data"), dict):
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        return value["data"]

    def _pr_closing_refs(self, repository: str, number: int) -> tuple[list[str], dict[str, Any]]:
        owner, name = repository.split("/", 1)
        query = """query($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){nameWithOwner defaultBranchRef{name} pullRequest(number:$number){id number state isDraft headRefOid baseRefName closingIssuesReferences(first:100,after:$cursor){nodes{id number state repository{nameWithOwner}} pageInfo{hasNextPage endCursor}}}}}"""
        cursor: str | None = None
        seen: set[str | None] = set()
        refs: list[str] = []
        metadata: dict[str, Any] | None = None
        while True:
            if cursor in seen:
                raise GitHubReadError("PAGINATION_INCOMPLETE")
            seen.add(cursor)
            data = self._graphql(query, {"owner": owner, "name": name, "number": number, "cursor": cursor})
            repo = data.get("repository")
            if not isinstance(repo, dict) or repo.get("nameWithOwner") != repository:
                raise GitHubReadError("IDENTITY_MISMATCH")
            pr = repo.get("pullRequest")
            if not isinstance(pr, dict):
                raise GitHubReadError("TARGET_AMBIGUOUS")
            connection = pr.get("closingIssuesReferences")
            if not isinstance(connection, dict) or not isinstance(connection.get("nodes"), list):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            for item in connection["nodes"]:
                if not isinstance(item, dict) or not isinstance(item.get("repository"), dict):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                if item["repository"].get("nameWithOwner") != repository:
                    raise GitHubReadError("CROSS_REPOSITORY_UNSUPPORTED")
                issue_number = item.get("number")
                if not isinstance(issue_number, int):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                refs.append(f"{repository}#{issue_number}")
            page = connection.get("pageInfo")
            if not isinstance(page, dict) or not isinstance(page.get("hasNextPage"), bool):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            metadata = {
                "head_oid": pr.get("headRefOid"),
                "base_ref_name": pr.get("baseRefName"),
                "default_branch": (repo.get("defaultBranchRef") or {}).get("name"),
                "state": pr.get("state"),
                "is_draft": pr.get("isDraft"),
            }
            if not page["hasNextPage"]:
                break
            cursor = page.get("endCursor")
            if not isinstance(cursor, str) or not cursor:
                raise GitHubReadError("PAGINATION_INCOMPLETE")
        assert metadata is not None
        return sorted(set(refs)), metadata

    def collect_pull_request(self, repository: str, number: int, merge_method: str) -> Mapping[str, Any]:
        errors: list[str] = []
        complete = True
        refs: list[str] = []
        metadata: dict[str, Any] = {}
        try:
            if merge_method not in {"merge", "rebase", "squash"}:
                raise GitHubReadError("MERGE_METHOD_UNKNOWN")
            refs, metadata = self._pr_closing_refs(repository, number)
            if metadata.get("state") != "OPEN" or metadata.get("is_draft") is True:
                # managed operation classifier/入口接続は #297。collector単独では
                # PR preconditionをIssue findingへ偽装せず判定不能として閉じる。
                errors.append("TARGET_AMBIGUOUS")
                complete = False
            if metadata.get("base_ref_name") != metadata.get("default_branch"):
                refs = []
            else:
                # merge-methodごとのmessage source再構築は #298 の collector 拡張責務。
                errors.append("MESSAGE_SOURCE_INCOMPLETE")
                complete = False
        except GitHubReadError as exc:
            errors.append(exc.reason)
            complete = False
        nodes, graph_errors, graph_complete = self._collect_graph(repository, refs)
        errors.extend(graph_errors)
        operation = fingerprint({"mode": "pr-merge", "repository": repository, "number": number, "merge_method": merge_method})
        binding = {
            "head_oid": metadata.get("head_oid"),
            "base_ref_name": metadata.get("base_ref_name"),
            "default_branch": metadata.get("default_branch"),
            "merge_method": merge_method if merge_method in {"merge", "rebase", "squash"} else None,
            "intercepted_commit_title_fingerprint": None,
            "intercepted_commit_message_fingerprint": None,
            "message_source_fingerprint": None,
            "delivered_message_fingerprint": None,
            "repository_merge_settings_fingerprint": None,
            "operation_fingerprint": operation,
            "snapshot_fingerprint": None,
            "attempt": 1,
        }
        return {
            "schema": SNAPSHOT_SCHEMA,
            "policy_version": POLICY_VERSION,
            "mode": "pr-merge",
            "repository": repository,
            "subject": {"type": "pull_request", "number": number},
            "roots": refs,
            "virtual_closed": refs,
            "nodes": nodes,
            "pages_complete": complete and graph_complete,
            "errors": sorted(set(errors)),
            "fetched_at": self._now(),
            "graphql_closing_set": refs,
            "delivered_message_closing_set": [],
            "binding": binding,
        }
