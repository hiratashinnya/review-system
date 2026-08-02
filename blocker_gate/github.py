"""GitHub 標準 API の read-only collector。"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .model import POLICY_VERSION, SNAPSHOT_SCHEMA, fingerprint
from .waiver import WaiverCollection, WaiverEvidence, WaiverMaterial

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

    @staticmethod
    def _pr_page_metadata(
        repo: Mapping[str, Any], pr: Mapping[str, Any], repository: str, number: int
    ) -> dict[str, Any]:
        if set(repo) != {"id", "nameWithOwner", "defaultBranchRef", "pullRequest"}:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        if repo.get("nameWithOwner") != repository or not isinstance(repo.get("id"), str) or not repo["id"]:
            raise GitHubReadError("IDENTITY_MISMATCH")
        default_ref = repo.get("defaultBranchRef")
        if not isinstance(default_ref, dict) or set(default_ref) != {"name"}:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        default_branch = default_ref.get("name")
        required_pr = {
            "id", "number", "state", "isDraft", "headRefOid", "baseRefName",
            "closingIssuesReferences",
        }
        if set(pr) != required_pr:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        if not isinstance(pr.get("id"), str) or not pr["id"]:
            raise GitHubReadError("IDENTITY_MISMATCH")
        if isinstance(pr.get("number"), bool) or pr.get("number") != number:
            raise GitHubReadError("IDENTITY_MISMATCH")
        if pr.get("state") not in {"OPEN", "CLOSED", "MERGED"} or not isinstance(pr.get("isDraft"), bool):
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        head_oid = pr.get("headRefOid")
        base_ref = pr.get("baseRefName")
        if not isinstance(head_oid, str) or not re.fullmatch(r"[0-9a-f]{40,64}", head_oid):
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        if not isinstance(base_ref, str) or not base_ref or not isinstance(default_branch, str) or not default_branch:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        return {
            "repository_node_id": repo["id"],
            "pr_node_id": pr["id"],
            "pr_number": pr["number"],
            "head_oid": head_oid,
            "base_ref_name": base_ref,
            "default_branch": default_branch,
            "state": pr["state"],
            "is_draft": pr["isDraft"],
        }

    def _pr_closing_refs(self, repository: str, number: int) -> tuple[list[str], dict[str, Any]]:
        owner, name = repository.split("/", 1)
        query = """query($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){id nameWithOwner defaultBranchRef{name} pullRequest(number:$number){id number state isDraft headRefOid baseRefName closingIssuesReferences(first:100,after:$cursor){nodes{id number state repository{nameWithOwner}} pageInfo{hasNextPage endCursor}}}}}"""
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
            if not isinstance(repo, dict):
                raise GitHubReadError("IDENTITY_MISMATCH")
            pr = repo.get("pullRequest")
            if not isinstance(pr, dict):
                raise GitHubReadError("TARGET_AMBIGUOUS")
            page_metadata = self._pr_page_metadata(repo, pr, repository, number)
            if metadata is None:
                metadata = page_metadata
            elif metadata != page_metadata:
                raise GitHubReadError("IDENTITY_MISMATCH")
            connection = pr.get("closingIssuesReferences")
            if not isinstance(connection, dict) or set(connection) != {"nodes", "pageInfo"} or not isinstance(connection.get("nodes"), list):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            for item in connection["nodes"]:
                if not isinstance(item, dict) or set(item) != {"id", "number", "state", "repository"} or not isinstance(item.get("repository"), dict):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                if set(item["repository"]) != {"nameWithOwner"} or item["repository"].get("nameWithOwner") != repository:
                    raise GitHubReadError("CROSS_REPOSITORY_UNSUPPORTED")
                issue_number = item.get("number")
                if isinstance(issue_number, bool) or not isinstance(issue_number, int) or issue_number < 1:
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                if not isinstance(item.get("id"), str) or not item["id"] or item.get("state") not in {"OPEN", "CLOSED"}:
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                refs.append(f"{repository}#{issue_number}")
            page = connection.get("pageInfo")
            if not isinstance(page, dict) or set(page) != {"hasNextPage", "endCursor"} or not isinstance(page.get("hasNextPage"), bool):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            if not page["hasNextPage"]:
                if page.get("endCursor") is not None and not isinstance(page.get("endCursor"), str):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                break
            cursor = page.get("endCursor")
            if not isinstance(cursor, str) or not cursor:
                raise GitHubReadError("PAGINATION_INCOMPLETE")
        assert metadata is not None
        return sorted(set(refs)), metadata

    def _merge_settings_fingerprint(
        self, repository: str, merge_method: str, repository_node_id: str
    ) -> str | None:
        if merge_method == "rebase":
            return None
        raw, _ = self._get(f"/repos/{repository}")
        if not isinstance(raw, dict) or raw.get("full_name") != repository or raw.get("node_id") != repository_node_id:
            raise GitHubReadError("IDENTITY_MISMATCH")
        if merge_method == "merge":
            names = ("merge_commit_title", "merge_commit_message")
            allowed = ({"PR_TITLE", "MERGE_MESSAGE"}, {"PR_TITLE", "PR_BODY", "BLANK"})
        else:
            names = ("squash_merge_commit_title", "squash_merge_commit_message")
            allowed = ({"PR_TITLE", "COMMIT_OR_PR_TITLE"}, {"PR_BODY", "COMMIT_MESSAGES", "BLANK"})
        values = [raw.get(name) for name in names]
        if any(value not in enums for value, enums in zip(values, allowed)):
            raise GitHubReadError("MERGE_SETTINGS_AMBIGUOUS")
        return fingerprint(
            {
                "repository_node_id": repository_node_id,
                "api_version": API_VERSION,
                "merge_method": merge_method,
                names[0]: values[0],
                names[1]: values[1],
            }
        )

    def _blob_bytes(self, repository: str, sha: str) -> bytes:
        raw, _ = self._get(f"/repos/{repository}/git/blobs/{sha}")
        if (
            not isinstance(raw, dict)
            or raw.get("sha") != sha
            or raw.get("encoding") != "base64"
            or not isinstance(raw.get("content"), str)
        ):
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        try:
            encoded = re.sub(r"\s+", "", raw["content"])
            return base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise GitHubReadError("API_PARTIAL_RESPONSE") from exc

    def collect_waiver_materials(self, repository: str) -> WaiverCollection:
        """current default head のwaiver真正性材料をread-onlyでfresh収集する。"""
        try:
            repo, _ = self._get(f"/repos/{repository}")
            if (
                not isinstance(repo, dict)
                or repo.get("full_name") != repository
                or not isinstance(repo.get("default_branch"), str)
                or not repo["default_branch"]
                or not isinstance(repo.get("node_id"), str)
                or not repo["node_id"]
            ):
                raise GitHubReadError("IDENTITY_MISMATCH")
            branch = repo["default_branch"]
            ref, _ = self._get(f"/repos/{repository}/git/ref/heads/{quote(branch, safe='')}")
            expected_ref = f"refs/heads/{branch}"
            obj = ref.get("object") if isinstance(ref, dict) else None
            if (
                not isinstance(ref, dict)
                or ref.get("ref") != expected_ref
                or not isinstance(obj, dict)
                or obj.get("type") != "commit"
                or not isinstance(obj.get("sha"), str)
                or not re.fullmatch(r"[0-9a-f]{40,64}", obj["sha"])
            ):
                raise GitHubReadError("IDENTITY_MISMATCH")
            head = obj["sha"]
            head_commit, _ = self._get(f"/repos/{repository}/git/commits/{head}")
            head_tree = head_commit.get("tree") if isinstance(head_commit, dict) else None
            if (
                not isinstance(head_commit, dict)
                or head_commit.get("sha") != head
                or not isinstance(head_tree, dict)
                or not isinstance(head_tree.get("sha"), str)
                or not re.fullmatch(r"[0-9a-f]{40,64}", head_tree["sha"])
            ):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            tree_sha = head_tree["sha"]
            tree, _ = self._get(f"/repos/{repository}/git/trees/{tree_sha}?recursive=1")
            entries = tree.get("tree") if isinstance(tree, dict) else None
            if (
                not isinstance(tree, dict)
                or tree.get("sha") != tree_sha
                or tree.get("truncated") is not False
                or not isinstance(entries, list)
            ):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            files: dict[str, str] = {}
            for item in entries:
                if not isinstance(item, dict):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                path = item.get("path")
                sha = item.get("sha")
                if item.get("type") == "blob" and isinstance(path, str) and isinstance(sha, str):
                    files[path] = sha
            waiver_paths = sorted(
                path
                for path in files
                if re.fullmatch(r"\.github/blocker-gate/waivers/[^/]+\.yml", path)
            )
            if not waiver_paths:
                return WaiverCollection()
            policy_path = ".github/blocker-gate/policy.yml"
            if policy_path not in files:
                return WaiverCollection(errors=("WAIVER_SCHEMA_INVALID",))
            policy_bytes = self._blob_bytes(repository, files[policy_path])

            rules, _ = self._get(
                f"/repos/{repository}/rules/branches/{quote(branch, safe='')}"
            )
            if not isinstance(rules, list) or any(not isinstance(rule, dict) for rule in rules):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            rule_types = {rule.get("type") for rule in rules}
            ruleset_ids = sorted(
                {
                    rule["ruleset_id"]
                    for rule in rules
                    if isinstance(rule.get("ruleset_id"), int) and not isinstance(rule.get("ruleset_id"), bool)
                }
            )
            ruleset_active = bool(ruleset_ids)
            history_bypass_free = bool(ruleset_ids)
            for ruleset_id in ruleset_ids:
                ruleset, _ = self._get(f"/repos/{repository}/rulesets/{ruleset_id}")
                if not isinstance(ruleset, dict) or ruleset.get("id") != ruleset_id:
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                ruleset_active = ruleset_active and ruleset.get("enforcement") == "active"
                history_bypass_free = history_bypass_free and ruleset.get("bypass_actors") == []

            materials: list[WaiverMaterial] = []
            for path in waiver_paths:
                waiver_bytes = self._blob_bytes(repository, files[path])
                encoded_path = quote(path, safe="")
                history, _ = self._get(
                    f"/repos/{repository}/commits?path={encoded_path}&sha={head}&per_page=1"
                )
                if not isinstance(history, list) or len(history) != 1 or not isinstance(history[0], dict):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                commit = history[0]
                approval = commit.get("sha")
                details = commit.get("commit")
                verification = details.get("verification") if isinstance(details, dict) else None
                author = commit.get("author")
                if not isinstance(approval, str) or not re.fullmatch(r"[0-9a-f]{40,64}", approval):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                compare, _ = self._get(f"/repos/{repository}/compare/{approval}...{head}")
                ancestor = isinstance(compare, dict) and compare.get("status") in {"ahead", "identical"}
                signer = author.get("login") if isinstance(author, dict) else None
                evidence = WaiverEvidence(
                    default_branch=branch,
                    default_head=head,
                    policy_blob_sha="sha256:" + hashlib.sha256(policy_bytes).hexdigest(),
                    waiver_blob_sha="sha256:" + hashlib.sha256(waiver_bytes).hexdigest(),
                    approval_commit=approval,
                    commit_is_default_head_ancestor=ancestor,
                    signature_verified=isinstance(verification, dict) and verification.get("verified") is True,
                    signer_login=signer if isinstance(signer, str) else None,
                    ruleset_active=ruleset_active,
                    history_bypass_free=history_bypass_free,
                    deletion_protected="deletion" in rule_types,
                    non_fast_forward_protected="non_fast_forward" in rule_types,
                )
                materials.append(WaiverMaterial(policy_bytes, waiver_bytes, evidence))
            return WaiverCollection(tuple(materials))
        except GitHubReadError as exc:
            return WaiverCollection(errors=(exc.reason,))

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
        settings_fingerprint: str | None = None
        try:
            if metadata:
                settings_fingerprint = self._merge_settings_fingerprint(
                    repository, merge_method, metadata["repository_node_id"]
                )
        except GitHubReadError as exc:
            errors.append(exc.reason)
            complete = False
        operation = fingerprint(
            {
                "mode": "pr-merge",
                "repository": repository,
                "repository_node_id": metadata.get("repository_node_id"),
                "pr_node_id": metadata.get("pr_node_id"),
                "number": number,
                "state": metadata.get("state"),
                "is_draft": metadata.get("is_draft"),
                "head_oid": metadata.get("head_oid"),
                "base_ref_name": metadata.get("base_ref_name"),
                "default_branch": metadata.get("default_branch"),
                "merge_method": merge_method,
            }
        )
        binding = {
            "head_oid": metadata.get("head_oid"),
            "base_ref_name": metadata.get("base_ref_name"),
            "default_branch": metadata.get("default_branch"),
            "merge_method": merge_method if merge_method in {"merge", "rebase", "squash"} else None,
            "intercepted_commit_title_fingerprint": None,
            "intercepted_commit_message_fingerprint": None,
            "message_source_fingerprint": None,
            "delivered_message_fingerprint": None,
            "repository_merge_settings_fingerprint": settings_fingerprint,
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
