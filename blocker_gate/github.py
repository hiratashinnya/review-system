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

from .auth import github_api_failure_reason
from .closing import (
    ClosingReferenceError,
    CommitMessageSource,
    DELIVERED_MESSAGE_FORMATTER_VERSION,
    SQUASH_COMMIT_MESSAGES_EVIDENCE_FINGERPRINT,
    build_delivered_messages,
    parse_closing_references,
)
from .model import POLICY_VERSION, SNAPSHOT_SCHEMA, classify_issue_state, fingerprint
from .snapshot import REPOSITORY_SNAPSHOT_SCHEMA
from .waiver import WaiverCollection, WaiverEvidence, WaiverMaterial

API_VERSION = "2026-03-10"
_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')
_GIT_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_GITHUB_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_RULESET_SOURCE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,98}[A-Za-z0-9])?$")
_RULESET_SOURCE_TYPES = frozenset({"Repository", "Organization", "Enterprise"})
_BRANCH_RULE_TYPES = frozenset(
    {
        "creation",
        "update",
        "deletion",
        "required_linear_history",
        "merge_queue",
        "required_deployments",
        "required_signatures",
        "pull_request",
        "required_status_checks",
        "non_fast_forward",
        "commit_message_pattern",
        "commit_author_email_pattern",
        "committer_email_pattern",
        "branch_name_pattern",
        "tag_name_pattern",
        "workflows",
        "code_scanning",
        "copilot_code_review",
        "license_compliance_scanning",
        "file_path_restriction",
        "max_file_path_length",
        "file_extension_restriction",
        "max_file_size",
    }
)


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
            # Issue #345［B］: HTTP 応答すら得られていない（DNS/接続/tunnel/timeout）。
            # GitHub が下した判断ではないので「到達不能」として分類する。
            raise GitHubReadError("API_UNREACHABLE") from exc


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
        # Issue #345 F-345-04: 直近の `collect_repository` が消費した GraphQL
        # rate limit。**telemetry 専用**で判定には一切使わないため、閉じた
        # snapshot schema へは載せず collector の属性として公開する
        # （`blocker-gate-repository-snapshot/v1` の top-level key は
        # `snapshot.parse_repository_snapshot` が完全一致で閉じている）。
        self.last_rate_limit: dict[str, Any] | None = None
        # Issue #466: 直近の収集で観測した「本 policy 版が説明できない state reason」
        # ＝未知語彙、および state と両立しない矛盾組み合わせ（F-466-02）。
        # `last_rate_limit` と同じく **telemetry 専用**で判定には一切使わないため、
        # 閉じた snapshot schema へは載せず collector の属性として公開する。
        # telemetry token（`REASON` または `STATE+REASON`）-> それを返した Issue ref の集合。
        self.unrecognized_state_reasons: dict[str, set[str]] = {}

    def _classify(self, ref: str, state: Any, reason: Any) -> str:
        """REST/GraphQL 双方が使う唯一の state 分類経路（Issue #466 AC4）。"""
        issue_class, unrecognized = classify_issue_state(state, reason)
        if unrecognized is not None:
            self.unrecognized_state_reasons.setdefault(unrecognized, set()).add(ref)
        return issue_class.value

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def _decode(self, status: int, headers: Mapping[str, str], body: bytes) -> Any:
        common_failure = github_api_failure_reason(status, headers)
        if common_failure is not None:
            raise GitHubReadError(common_failure)
        if status in {404, 410}:
            raise GitHubReadError("RELATION_TARGET_UNREADABLE")
        if not 200 <= status < 300:
            raise GitHubReadError("API_UNAVAILABLE")
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GitHubReadError("API_PARTIAL_RESPONSE") from exc

    def _get(self, path_or_url: str) -> tuple[Any, Mapping[str, str]]:
        url = path_or_url if path_or_url.startswith("https://") else "https://api.github.com" + path_or_url
        status, headers, body = self._transport.get(url, self._headers)
        return self._decode(status, headers, body), headers

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
                    "state": self._classify(
                        ref, issue.get("state"), issue.get("state_reason")
                    ),
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
        self.unrecognized_state_reasons = {}
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

    # Issue #345［A］: repository 全体の Issue graph を GraphQL で一括取得する。
    # REST collector（1 Issue あたり最低3 request）を全 open Issue へ広げると
    # 実測 277 requests/回 になり、Actions の GITHUB_TOKEN 枠 1,000 requests/h を
    # cron 5分で 3.3 倍超過する。GraphQL なら数 request/回に収まる。
    #
    # states filter を掛けず **全 Issue**（closed を含む）を列挙するのは、
    # `evaluator.validate_graph` が parent/child の双方向一致と全 relation target の
    # 存在を要求するため。open だけを引くと closed の子/親の逆参照を埋められず、
    # 正しい graph が RELATION_INCONSISTENT で常時 fail-close する。
    #
    # nested connection の `first:50` は Issue #345 の cost 実測と同じ形。
    # 50 を超える relation は補完せず `PAGINATION_INCOMPLETE` で fail-close する
    # （policy §3.1 の「全 page 完走」を満たせない状態を ALLOW へ倒さない）。
    #
    # Issue #345 F-345-04: `rateLimit` を top-level（`repository` の兄弟）で
    # 併せて引き、cron 5分の実消費を事後に検証できるようにする（D-345-1 の
    # 見積り「測定値の約4倍」を裏付ける実測値が無いと、枠内に収まっている
    # ことを誰も確認できない）。`rateLimit` 自体は判定材料ではなく telemetry。
    _REPOSITORY_QUERY = (
        "query($owner:String!,$name:String!,$cursor:String){"
        "rateLimit{cost remaining resetAt} "
        "repository(owner:$owner,name:$name){nameWithOwner "
        "issues(first:100,after:$cursor,orderBy:{field:CREATED_AT,direction:ASC}){"
        "pageInfo{hasNextPage endCursor} "
        "nodes{id number state stateReason title url "
        "parent{number repository{nameWithOwner}} "
        "blockedBy(first:50){pageInfo{hasNextPage} nodes{number repository{nameWithOwner}}} "
        "subIssues(first:50){pageInfo{hasNextPage} nodes{number repository{nameWithOwner}}}"
        "}}}}"
    )

    @staticmethod
    def _graphql_ref(repository: str, raw: Any) -> str:
        """cross-repository な relation target を無言で落とさず、明示的に弾く。"""
        if not isinstance(raw, dict) or set(raw) != {"number", "repository"}:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        number = raw["number"]
        owner = raw["repository"]
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        if not isinstance(owner, dict) or set(owner) != {"nameWithOwner"}:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        if owner["nameWithOwner"] != repository:
            raise GitHubReadError("CROSS_REPOSITORY_UNSUPPORTED")
        return f"{repository}#{number}"

    def _graphql_relation(
        self, repository: str, connection: Any, errors: list[str]
    ) -> tuple[list[str], bool]:
        if (
            not isinstance(connection, dict)
            or set(connection) != {"pageInfo", "nodes"}
            or not isinstance(connection["nodes"], list)
            or not isinstance(connection["pageInfo"], dict)
            or set(connection["pageInfo"]) != {"hasNextPage"}
            or not isinstance(connection["pageInfo"]["hasNextPage"], bool)
        ):
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        complete = not connection["pageInfo"]["hasNextPage"]
        if not complete:
            errors.append("PAGINATION_INCOMPLETE")
        refs: list[str] = []
        for item in connection["nodes"]:
            try:
                refs.append(self._graphql_ref(repository, item))
            except GitHubReadError as exc:
                if exc.reason != "CROSS_REPOSITORY_UNSUPPORTED":
                    raise
                errors.append(exc.reason)
                complete = False
        return sorted(set(refs)), complete

    @staticmethod
    def _accumulate_rate_limit(raw: Any, usage: dict[str, Any]) -> None:
        """GraphQL の ``rateLimit`` を **telemetry としてだけ** 積む（F-345-04）。

        `cost` は page をまたいで合計し、`remaining`/`resetAt` は最後に観測した
        値を採る（残量は単調に変化するので最新が実態に一番近い）。

        **欠落・型不正でも例外にしない。** この値は verdict にも snapshot 内容にも
        一切影響しない診断情報であり、ここで fail-close させると「rate limit を
        測るために snapshot 生成が落ちる」という本末転倒になる。読めなかった場合は
        単に要約へ出さない（読めた page 数 `pages` が 0 のままになる）。
        """
        if not isinstance(raw, dict):
            return
        cost = raw.get("cost")
        remaining = raw.get("remaining")
        reset_at = raw.get("resetAt")
        if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
            return
        usage["cost"] += cost
        usage["pages"] += 1
        if not isinstance(remaining, bool) and isinstance(remaining, int) and remaining >= 0:
            usage["remaining"] = remaining
        if isinstance(reset_at, str) and reset_at:
            usage["reset_at"] = reset_at

    def collect_repository(self, repository: str) -> Mapping[str, Any]:
        """repository 全体の Issue graph を ``blocker-gate-repository-snapshot/v1`` にする。

        ``pages_complete``/``errors`` は repository 全体で1組しか持たない。
        1 Issue の収集失敗が全 Issue を fail-close させるが、fail-close 側の
        過剰なので許容する（Issue #345 で意図した挙動として test で固定）。
        """
        if repository.count("/") != 1:
            raise GitHubReadError("IDENTITY_MISMATCH")
        owner, name = repository.split("/", 1)
        issues: dict[str, Any] = {}
        errors: list[str] = []
        complete = True
        usage: dict[str, Any] = {"cost": 0, "pages": 0, "remaining": None, "reset_at": None}
        self.last_rate_limit = None
        self.unrecognized_state_reasons = {}
        try:
            cursor: str | None = None
            seen: set[str | None] = set()
            while True:
                if cursor in seen:
                    raise GitHubReadError("PAGINATION_INCOMPLETE")
                seen.add(cursor)
                data = self._graphql(
                    self._REPOSITORY_QUERY,
                    {"owner": owner, "name": name, "cursor": cursor},
                )
                self._accumulate_rate_limit(data.get("rateLimit"), usage)
                repo = data.get("repository")
                if not isinstance(repo, dict) or set(repo) != {"nameWithOwner", "issues"}:
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                if repo["nameWithOwner"] != repository:
                    raise GitHubReadError("IDENTITY_MISMATCH")
                connection = repo["issues"]
                if (
                    not isinstance(connection, dict)
                    or set(connection) != {"pageInfo", "nodes"}
                    or not isinstance(connection["nodes"], list)
                ):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                for raw in connection["nodes"]:
                    expected = {
                        "id", "number", "state", "stateReason", "title", "url",
                        "parent", "blockedBy", "subIssues",
                    }
                    if not isinstance(raw, dict) or set(raw) != expected:
                        raise GitHubReadError("API_PARTIAL_RESPONSE")
                    number = raw["number"]
                    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
                        raise GitHubReadError("API_PARTIAL_RESPONSE")
                    ref = f"{repository}#{number}"
                    if ref in issues:
                        raise GitHubReadError("IDENTITY_MISMATCH")
                    if not isinstance(raw["id"], str) or not raw["id"]:
                        raise GitHubReadError("IDENTITY_MISMATCH")
                    title = raw["title"]
                    url = raw["url"]
                    if not isinstance(title, str) or not isinstance(url, str) or not url:
                        raise GitHubReadError("API_PARTIAL_RESPONSE")
                    blocked, blocked_ok = self._graphql_relation(
                        repository, raw["blockedBy"], errors
                    )
                    children, children_ok = self._graphql_relation(
                        repository, raw["subIssues"], errors
                    )
                    parent: str | None = None
                    if raw["parent"] is not None:
                        try:
                            parent = self._graphql_ref(repository, raw["parent"])
                        except GitHubReadError as exc:
                            if exc.reason != "CROSS_REPOSITORY_UNSUPPORTED":
                                raise
                            errors.append(exc.reason)
                            complete = False
                    complete = complete and blocked_ok and children_ok
                    issues[ref] = {
                        "node_id": raw["id"],
                        "state": self._classify(ref, raw["state"], raw["stateReason"]),
                        "blocked_by": blocked,
                        "parent": parent,
                        "children": children,
                        # title が空の Issue は GitHub 上作れないが、deny report が
                        # 空文字になるのを避けるため ref で代替する。
                        "title": title or ref,
                        "url": url,
                    }
                    if len(issues) > 10_000:
                        raise GitHubReadError("GRAPH_LIMIT_EXCEEDED")
                page = connection["pageInfo"]
                if (
                    not isinstance(page, dict)
                    or set(page) != {"hasNextPage", "endCursor"}
                    or not isinstance(page["hasNextPage"], bool)
                ):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                if not page["hasNextPage"]:
                    break
                cursor = page["endCursor"]
                if not isinstance(cursor, str) or not cursor:
                    raise GitHubReadError("PAGINATION_INCOMPLETE")
        except GitHubReadError as exc:
            errors.append(exc.reason)
            complete = False
        self.last_rate_limit = usage if usage["pages"] else None
        return {
            "schema": REPOSITORY_SNAPSHOT_SCHEMA,
            "policy_version": POLICY_VERSION,
            "repository": repository,
            "generated_at": self._now(),
            "pages_complete": complete,
            "errors": sorted(set(errors)),
            "issues": issues,
        }

    def _graphql(self, query: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        headers = dict(self._headers)
        headers["Content-Type"] = "application/json"
        body = json.dumps({"query": query, "variables": variables}, separators=(",", ":")).encode("utf-8")
        status, response_headers, raw = self._transport.post(
            "https://api.github.com/graphql", headers, body
        )
        value = self._decode(status, response_headers, raw)
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
            "title", "body", "headRefName", "headRepositoryOwner", "closingIssuesReferences",
            "commits",
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
        commits = pr.get("commits")
        if type(head_oid) is not str or not _GIT_OID.fullmatch(head_oid):
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        if not isinstance(base_ref, str) or not base_ref or not isinstance(default_branch, str) or not default_branch:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        if (
            not isinstance(commits, dict)
            or set(commits) != {"totalCount"}
            or isinstance(commits.get("totalCount"), bool)
            or not isinstance(commits.get("totalCount"), int)
            or commits["totalCount"] < 1
        ):
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        title = pr.get("title")
        body = pr.get("body")
        head_ref_name = pr.get("headRefName")
        head_owner = pr.get("headRepositoryOwner")
        if (
            not isinstance(title, str)
            or body is not None and not isinstance(body, str)
            or not isinstance(head_ref_name, str)
            or not head_ref_name
            or not isinstance(head_owner, dict)
            or set(head_owner) != {"login"}
            or not isinstance(head_owner.get("login"), str)
            or not head_owner["login"]
        ):
            raise GitHubReadError("MESSAGE_SOURCE_INCOMPLETE")
        return {
            "repository_node_id": repo["id"],
            "pr_node_id": pr["id"],
            "pr_number": pr["number"],
            "head_oid": head_oid,
            "base_ref_name": base_ref,
            "default_branch": default_branch,
            "state": pr["state"],
            "is_draft": pr["isDraft"],
            "commit_count": commits["totalCount"],
            "title": title,
            "body": body or "",
            "head_label": f"{head_owner['login']}:{head_ref_name}",
        }

    def _pr_closing_refs(
        self,
        repository: str,
        number: int,
        available_metadata: dict[str, Any] | None = None,
    ) -> tuple[list[str], dict[str, Any]]:
        owner, name = repository.split("/", 1)
        query = """query($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){id nameWithOwner defaultBranchRef{name} pullRequest(number:$number){id number state isDraft headRefOid baseRefName title body headRefName headRepositoryOwner{login} commits{totalCount} closingIssuesReferences(first:100,after:$cursor){nodes{id number state repository{nameWithOwner}} pageInfo{hasNextPage endCursor}}}}}"""
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
                if available_metadata is not None:
                    available_metadata.clear()
                    available_metadata.update(page_metadata)
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

    def _merge_settings(
        self, repository: str, merge_method: str, repository_node_id: str
    ) -> tuple[dict[str, str] | None, str | None]:
        if merge_method == "rebase":
            return None, None
        raw, _ = self._get(f"/repos/{repository}")
        if not isinstance(raw, dict) or raw.get("full_name") != repository or raw.get("node_id") != repository_node_id:
            raise GitHubReadError("IDENTITY_MISMATCH")
        if merge_method == "merge":
            names = ("merge_commit_title", "merge_commit_message")
            allowed = ({"PR_TITLE", "MERGE_MESSAGE"}, {"PR_TITLE", "PR_BODY", "BLANK"})
        else:
            names = ("squash_merge_commit_title", "squash_merge_commit_message")
            allowed = ({"PR_TITLE", "COMMIT_OR_PR_TITLE"}, {"PR_BODY", "COMMIT_MESSAGES", "BLANK"})
        values: list[str] = []
        for name, enums in zip(names, allowed):
            value = raw.get(name)
            if not isinstance(value, str) or value not in enums:
                raise GitHubReadError("MERGE_SETTINGS_AMBIGUOUS")
            values.append(value)
        settings = {names[0]: values[0], names[1]: values[1]}
        return settings, fingerprint(
            {
                "repository_node_id": repository_node_id,
                "api_version": API_VERSION,
                "merge_method": merge_method,
                "delivered_message_formatter_version": DELIVERED_MESSAGE_FORMATTER_VERSION,
                "squash_commit_messages_evidence_fingerprint": (
                    SQUASH_COMMIT_MESSAGES_EVIDENCE_FINGERPRINT
                    if merge_method == "squash"
                    and settings.get("squash_merge_commit_message") == "COMMIT_MESSAGES"
                    else None
                ),
                **settings,
            }
        )

    def _merge_settings_fingerprint(
        self, repository: str, merge_method: str, repository_node_id: str
    ) -> str | None:
        """後方互換用にsettings fingerprintだけを返す。"""
        return self._merge_settings(repository, merge_method, repository_node_id)[1]

    def _pr_commit_sources(
        self, repository: str, number: int
    ) -> tuple[CommitMessageSource, ...]:
        sources: list[CommitMessageSource] = []
        seen_oids: set[str] = set()
        for raw in self._list(f"/repos/{repository}/pulls/{number}/commits"):
            oid = raw.get("sha")
            commit = raw.get("commit")
            parents = raw.get("parents")
            if (
                not isinstance(oid, str)
                or not _GIT_OID.fullmatch(oid)
                or not isinstance(commit, dict)
                or not isinstance(parents, list)
                or any(not isinstance(parent, dict) for parent in parents)
            ):
                raise GitHubReadError("MESSAGE_SOURCE_INCOMPLETE")
            if oid in seen_oids:
                raise GitHubReadError("MESSAGE_SOURCE_INCOMPLETE")
            seen_oids.add(oid)
            message = commit.get("message")
            tree = commit.get("tree")
            if (
                not isinstance(message, str)
                or not isinstance(tree, dict)
                or not isinstance(tree.get("sha"), str)
                or not _GIT_OID.fullmatch(tree["sha"])
            ):
                raise GitHubReadError("MESSAGE_SOURCE_INCOMPLETE")
            parent_oids: list[str] = []
            for parent in parents:
                parent_oid = parent.get("sha")
                if not isinstance(parent_oid, str) or not _GIT_OID.fullmatch(parent_oid):
                    raise GitHubReadError("MESSAGE_SOURCE_INCOMPLETE")
                parent_oids.append(parent_oid)
            first_parent_tree: str | None = None
            if len(parent_oids) == 1:
                parent_raw, _ = self._get(
                    f"/repos/{repository}/git/commits/{quote(parent_oids[0], safe='')}"
                )
                parent_tree = parent_raw.get("tree") if isinstance(parent_raw, dict) else None
                if (
                    not isinstance(parent_tree, dict)
                    or not isinstance(parent_tree.get("sha"), str)
                    or not _GIT_OID.fullmatch(parent_tree["sha"])
                ):
                    raise GitHubReadError("MESSAGE_SOURCE_INCOMPLETE")
                first_parent_tree = parent_tree["sha"]
            sources.append(
                CommitMessageSource(
                    oid=oid,
                    message=message,
                    tree_oid=tree["sha"],
                    parent_oids=tuple(parent_oids),
                    first_parent_tree_oid=first_parent_tree,
                )
            )
        if not sources:
            raise GitHubReadError("MESSAGE_SOURCE_INCOMPLETE")
        return tuple(sources)

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

    def _approval_signer(self, repository: str, approval: str) -> str:
        """approval commitと署名状態・署名者を単一GraphQL応答で束縛する。"""
        if repository.count("/") != 1:
            raise GitHubReadError("IDENTITY_MISMATCH")
        owner, name = repository.split("/", 1)
        query = """
        query($owner:String!,$name:String!,$oid:GitObjectID!){
          repository(owner:$owner,name:$name){
            nameWithOwner
            object(oid:$oid){
              ... on Commit{
                oid
                signature{isValid state signer{login} wasSignedByGitHub}
              }
            }
          }
        }
        """
        data = self._graphql(query, {"owner": owner, "name": name, "oid": approval})
        if type(data) is not dict or set(data) != {"repository"}:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        repo = data["repository"]
        if type(repo) is not dict or set(repo) != {"nameWithOwner", "object"}:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        if repo["nameWithOwner"] != repository:
            raise GitHubReadError("IDENTITY_MISMATCH")
        commit = repo["object"]
        if type(commit) is not dict or set(commit) != {"oid", "signature"}:
            raise GitHubReadError("API_PARTIAL_RESPONSE")
        if commit["oid"] != approval:
            raise GitHubReadError("IDENTITY_MISMATCH")
        signature = commit["signature"]
        if type(signature) is not dict or set(signature) != {
            "isValid",
            "state",
            "signer",
            "wasSignedByGitHub",
        }:
            raise GitHubReadError("WAIVER_INVALID")
        signer = signature["signer"]
        if (
            signature["isValid"] is not True
            or signature["state"] != "VALID"
            or type(signature["wasSignedByGitHub"]) is not bool
            or type(signer) is not dict
            or set(signer) != {"login"}
            or type(signer["login"]) is not str
            or not _GITHUB_LOGIN.fullmatch(signer["login"])
        ):
            raise GitHubReadError("WAIVER_INVALID")
        return signer["login"]

    @staticmethod
    def _ruleset_source_valid(repository: str, source_type: str, source: str) -> bool:
        if source_type == "Repository":
            return source == repository
        if source_type == "Organization":
            return source == repository.split("/", 1)[0]
        return bool(_RULESET_SOURCE.fullmatch(source))

    def _branch_protection_evidence(
        self, repository: str, branch: str
    ) -> tuple[bool, bool, bool, bool]:
        """同一rulesetに閉じた履歴保護だけをwaiver証拠へ昇格する。"""
        rules = self._list(f"/repos/{repository}/rules/branches/{quote(branch, safe='')}")
        by_type: dict[str, set[tuple[int, str, str]]] = {}
        seen: set[tuple[str, int, str, str]] = set()
        core_keys = {"type", "ruleset_source_type", "ruleset_source", "ruleset_id"}
        for rule in rules:
            keys = set(rule)
            if not core_keys.issubset(keys) or not keys.issubset(core_keys | {"parameters"}):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            rule_type = rule["type"]
            source_type = rule["ruleset_source_type"]
            source = rule["ruleset_source"]
            ruleset_id = rule["ruleset_id"]
            if (
                type(rule_type) is not str
                or rule_type not in _BRANCH_RULE_TYPES
                or type(source_type) is not str
                or source_type not in _RULESET_SOURCE_TYPES
                or type(source) is not str
                or not self._ruleset_source_valid(repository, source_type, source)
                or type(ruleset_id) is not int
                or ruleset_id < 1
                or ("parameters" in rule and type(rule["parameters"]) is not dict)
            ):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            identity = (ruleset_id, source_type, source)
            item_key = (rule_type, *identity)
            if item_key in seen:
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            seen.add(item_key)
            by_type.setdefault(rule_type, set()).add(identity)

        candidates = by_type.get("deletion", set()) & by_type.get(
            "non_fast_forward", set()
        )
        if not candidates:
            return False, False, False, False

        active_seen = False
        for ruleset_id, source_type, source in sorted(candidates):
            ruleset, _ = self._get(
                f"/repos/{repository}/rulesets/{ruleset_id}?includes_parents=true"
            )
            if type(ruleset) is not dict:
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            required = {
                "id",
                "target",
                "source_type",
                "source",
                "enforcement",
                "bypass_actors",
                "rules",
            }
            if not required.issubset(ruleset):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            if (
                type(ruleset["id"]) is not int
                or ruleset["id"] != ruleset_id
                or type(ruleset["target"]) is not str
                or ruleset["target"] != "branch"
                or type(ruleset["source_type"]) is not str
                or ruleset["source_type"] != source_type
                or type(ruleset["source"]) is not str
                or ruleset["source"] != source
                or type(ruleset["enforcement"]) is not str
                or ruleset["enforcement"] not in {"active", "evaluate", "disabled"}
                or type(ruleset["bypass_actors"]) is not list
                or type(ruleset["rules"]) is not list
            ):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            detail_types: set[str] = set()
            for detail_rule in ruleset["rules"]:
                if (
                    type(detail_rule) is not dict
                    or type(detail_rule.get("type")) is not str
                    or detail_rule["type"] not in _BRANCH_RULE_TYPES
                ):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                if detail_rule["type"] in {"deletion", "non_fast_forward"} and set(
                    detail_rule
                ) != {"type"}:
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                detail_types.add(detail_rule["type"])
            if not {"deletion", "non_fast_forward"}.issubset(detail_types):
                raise GitHubReadError("API_PARTIAL_RESPONSE")
            active = ruleset["enforcement"] == "active"
            active_seen = active_seen or active
            if active and ruleset["bypass_actors"] == []:
                return True, True, True, True
        return active_seen, False, False, False

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
                or type(obj.get("sha")) is not str
                or not _GIT_OID.fullmatch(obj["sha"])
            ):
                raise GitHubReadError("IDENTITY_MISMATCH")
            head = obj["sha"]
            head_commit, _ = self._get(f"/repos/{repository}/git/commits/{head}")
            head_tree = head_commit.get("tree") if isinstance(head_commit, dict) else None
            if (
                not isinstance(head_commit, dict)
                or head_commit.get("sha") != head
                or not isinstance(head_tree, dict)
                or type(head_tree.get("sha")) is not str
                or not _GIT_OID.fullmatch(head_tree["sha"])
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

            (
                ruleset_active,
                history_bypass_free,
                deletion_protected,
                non_fast_forward_protected,
            ) = self._branch_protection_evidence(repository, branch)

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
                if type(approval) is not str or not _GIT_OID.fullmatch(approval):
                    raise GitHubReadError("API_PARTIAL_RESPONSE")
                signer = self._approval_signer(repository, approval)
                compare, _ = self._get(f"/repos/{repository}/compare/{approval}...{head}")
                ancestor = isinstance(compare, dict) and compare.get("status") in {"ahead", "identical"}
                evidence = WaiverEvidence(
                    default_branch=branch,
                    default_head=head,
                    policy_blob_sha="sha256:" + hashlib.sha256(policy_bytes).hexdigest(),
                    waiver_blob_sha="sha256:" + hashlib.sha256(waiver_bytes).hexdigest(),
                    approval_commit=approval,
                    commit_is_default_head_ancestor=ancestor,
                    signature_verified=True,
                    signer_login=signer,
                    ruleset_active=ruleset_active,
                    history_bypass_free=history_bypass_free,
                    deletion_protected=deletion_protected,
                    non_fast_forward_protected=non_fast_forward_protected,
                )
                materials.append(WaiverMaterial(policy_bytes, waiver_bytes, evidence))
            return WaiverCollection(tuple(materials))
        except GitHubReadError as exc:
            return WaiverCollection(errors=(exc.reason,))

    def collect_pull_request(
        self,
        repository: str,
        number: int,
        merge_method: str,
        *,
        commit_title: str | None = None,
        commit_message: str | None = None,
        expected_head_oid: str | None = None,
        operation_fingerprint: str | None = None,
        attempt: int = 1,
    ) -> Mapping[str, Any]:
        self.unrecognized_state_reasons = {}
        errors: list[str] = []
        complete = True
        graphql_refs: list[str] = []
        delivered_refs: list[str] = []
        metadata: dict[str, Any] = {}
        settings_fingerprint: str | None = None
        message_source_fingerprint: str | None = None
        delivered_message_fingerprint: str | None = None
        try:
            if merge_method not in {"merge", "rebase", "squash"}:
                raise GitHubReadError("MERGE_METHOD_UNKNOWN")
            if (
                commit_title is not None and not isinstance(commit_title, str)
                or commit_message is not None and not isinstance(commit_message, str)
            ):
                raise GitHubReadError("MERGE_OVERRIDE_AMBIGUOUS")
            if expected_head_oid is not None and (
                not isinstance(expected_head_oid, str) or not _GIT_OID.fullmatch(expected_head_oid)
            ):
                raise GitHubReadError("IDENTITY_MISMATCH")
            if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt not in {1, 2, 3}:
                raise GitHubReadError("REEVALUATION_LIMIT")
            graphql_refs, metadata = self._pr_closing_refs(
                repository, number, metadata
            )
            if expected_head_oid is not None and metadata.get("head_oid") != expected_head_oid:
                raise GitHubReadError("IDENTITY_MISMATCH")
            if metadata.get("base_ref_name") != metadata.get("default_branch"):
                graphql_refs = []
                _, settings_fingerprint = self._merge_settings(
                    repository, merge_method, metadata["repository_node_id"]
                )
            else:
                settings, settings_fingerprint = self._merge_settings(
                    repository, merge_method, metadata["repository_node_id"]
                )
                commits = self._pr_commit_sources(repository, number)
                if (
                    len(commits) != metadata.get("commit_count")
                    or commits[-1].oid != metadata.get("head_oid")
                ):
                    raise GitHubReadError("IDENTITY_MISMATCH")
                bundle = build_delivered_messages(
                    repository=repository,
                    number=number,
                    merge_method=merge_method,
                    pr_title=metadata["title"],
                    pr_body=metadata["body"],
                    head_label=metadata["head_label"],
                    commits=commits,
                    settings=settings,
                    commit_title=commit_title,
                    commit_message=commit_message,
                )
                delivered_refs = list(
                    parse_closing_references(bundle.messages, repository)
                )
                message_source_fingerprint = bundle.message_source_fingerprint
                delivered_message_fingerprint = bundle.delivered_message_fingerprint
        except GitHubReadError as exc:
            errors.append(exc.reason)
            complete = False
        except ClosingReferenceError as exc:
            errors.append(exc.reason)
            complete = False
        refs = sorted(set(graphql_refs) | set(delivered_refs))
        nodes, graph_errors, graph_complete = self._collect_graph(repository, refs)
        errors.extend(graph_errors)
        operation = operation_fingerprint or fingerprint(
            {
                "mode": "pr-merge",
                "repository": repository,
                "repository_node_id": metadata.get("repository_node_id"),
                "pr_node_id": metadata.get("pr_node_id"),
                "number": number,
                "state": metadata.get("state"),
                "is_draft": metadata.get("is_draft"),
                "head_oid": metadata.get("head_oid"),
                "expected_commit_count": metadata.get("commit_count"),
                "base_ref_name": metadata.get("base_ref_name"),
                "default_branch": metadata.get("default_branch"),
                "merge_method": merge_method,
                "commit_title": commit_title,
                "commit_message": commit_message,
                "expected_head_oid": expected_head_oid,
            }
        )
        binding = {
            "head_oid": metadata.get("head_oid"),
            "expected_commit_count": metadata.get("commit_count"),
            "base_ref_name": metadata.get("base_ref_name"),
            "default_branch": metadata.get("default_branch"),
            "merge_method": merge_method if merge_method in {"merge", "rebase", "squash"} else None,
            "intercepted_commit_title_fingerprint": (
                fingerprint({"value": commit_title}) if commit_title is not None else None
            ),
            "intercepted_commit_message_fingerprint": (
                fingerprint({"value": commit_message}) if commit_message is not None else None
            ),
            "message_source_fingerprint": message_source_fingerprint,
            "delivered_message_fingerprint": delivered_message_fingerprint,
            "repository_merge_settings_fingerprint": settings_fingerprint,
            "operation_fingerprint": operation,
            "snapshot_fingerprint": None,
            "attempt": attempt,
            "pr_state": metadata.get("state"),
            "pr_is_draft": metadata.get("is_draft"),
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
            "graphql_closing_set": sorted(set(graphql_refs)),
            "delivered_message_closing_set": sorted(set(delivered_refs)),
            "binding": binding,
        }
