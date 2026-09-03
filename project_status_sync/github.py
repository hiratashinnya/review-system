"""Projects V2 GraphQL adapter（Status field だけを読み、Status field だけを書く）。

依存仕様: Issue #460 Scope §1/§4。認証は classic PAT（scope `project`）を
``PROJECT_SYNC_TOKEN`` から受け取る。Actions の ``GITHUB_TOKEN`` では Projects V2 に
書き込めないため、fallback で ``GITHUB_TOKEN`` を拾うことはしない——拾うと
「権限不足で失敗する」のか「secret を設定し忘れた」のか区別できなくなる。

field id / option id を live 解決する理由: (a) 語彙外 option（オーナーが後から
追加した Status）を検出するには option 一覧を読む必要があり、読むなら id も同時に
得られる、(b) id を定数で持つと field を作り直したときに静かに別 field を指しうる。
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from blocker_gate.auth import github_api_failure_reason

from .model import STATUS_FIELD_NAME, ProjectItem, ProjectView

GRAPHQL_ENDPOINT = "https://api.github.com/graphql"
TOKEN_ENV = "PROJECT_SYNC_TOKEN"
USER_AGENT = "review-system-project-status-sync/1.0"

_PROJECT_QUERY = (
    "query($project:ID!,$cursor:String){"
    "node(id:$project){__typename "
    "... on ProjectV2{id number title "
    'field(name:"' + STATUS_FIELD_NAME + '"){__typename '
    "... on ProjectV2SingleSelectField{id name options{id name}}} "
    "items(first:100,after:$cursor){"
    "pageInfo{hasNextPage endCursor} "
    "nodes{id "
    'fieldValueByName(name:"' + STATUS_FIELD_NAME + '"){__typename '
    "... on ProjectV2ItemFieldSingleSelectValue{optionId name}} "
    "content{__typename ... on Issue{number repository{nameWithOwner}}}"
    "}}}}}"
)

_UPDATE_MUTATION = (
    "mutation($project:ID!,$item:ID!,$field:ID!,$option:String!){"
    "updateProjectV2ItemFieldValue(input:{projectId:$project,itemId:$item,"
    "fieldId:$field,value:{singleSelectOptionId:$option}}){"
    "projectV2Item{id}}}"
)


class ProjectSyncApiError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Transport(Protocol):
    def post(
        self, url: str, headers: Mapping[str, str], body: bytes
    ) -> tuple[int, Mapping[str, str], bytes]: ...


class UrlLibTransport:
    def post(
        self, url: str, headers: Mapping[str, str], body: bytes
    ) -> tuple[int, Mapping[str, str], bytes]:
        request = Request(url, data=body, headers=dict(headers), method="POST")
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub URL
                return response.status, dict(response.headers.items()), response.read()
        except HTTPError as exc:
            return exc.code, dict(exc.headers.items()), exc.read()
        except (TimeoutError, URLError) as exc:
            raise ProjectSyncApiError("API_UNREACHABLE") from exc


def resolve_token(environ: Mapping[str, str] | None = None) -> str:
    values = os.environ if environ is None else environ
    token = values.get(TOKEN_ENV)
    if not isinstance(token, str) or not token.strip():
        raise ProjectSyncApiError("TOKEN_MISSING")
    return token.strip()


class ProjectStatusClient:
    def __init__(self, token: str, transport: Transport | None = None) -> None:
        self._transport = transport or UrlLibTransport()
        self._headers = {
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Authorization": "Bearer " + token,
        }

    def _graphql(self, query: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        body = json.dumps(
            {"query": query, "variables": dict(variables)}, separators=(",", ":")
        ).encode("utf-8")
        status, headers, raw = self._transport.post(GRAPHQL_ENDPOINT, self._headers, body)
        failure = github_api_failure_reason(status, headers)
        if failure is not None:
            raise ProjectSyncApiError(failure)
        if not 200 <= status < 300:
            raise ProjectSyncApiError("API_UNAVAILABLE")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProjectSyncApiError("API_PARTIAL_RESPONSE") from exc
        if not isinstance(value, dict) or value.get("errors"):
            raise ProjectSyncApiError("API_PARTIAL_RESPONSE")
        data = value.get("data")
        if not isinstance(data, dict):
            raise ProjectSyncApiError("API_PARTIAL_RESPONSE")
        return data

    @staticmethod
    def _status_field(raw: Any) -> tuple[str, dict[str, str]]:
        if (
            not isinstance(raw, dict)
            or raw.get("__typename") != "ProjectV2SingleSelectField"
            or raw.get("name") != STATUS_FIELD_NAME
            or not isinstance(raw.get("id"), str)
            or not raw["id"]
            or not isinstance(raw.get("options"), list)
        ):
            raise ProjectSyncApiError("STATUS_FIELD_UNREADABLE")
        options: dict[str, str] = {}
        for option in raw["options"]:
            if (
                not isinstance(option, dict)
                or not isinstance(option.get("id"), str)
                or not option["id"]
                or not isinstance(option.get("name"), str)
                or not option["name"]
            ):
                raise ProjectSyncApiError("STATUS_FIELD_UNREADABLE")
            if option["name"] in options:
                raise ProjectSyncApiError("STATUS_FIELD_UNREADABLE")
            options[option["name"]] = option["id"]
        return raw["id"], options

    @staticmethod
    def _item(raw: Any, repository: str) -> ProjectItem:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"]:
            raise ProjectSyncApiError("API_PARTIAL_RESPONSE")
        content = raw.get("content")
        issue_ref: str | None = None
        content_type = "Unknown"
        if isinstance(content, dict):
            content_type = content.get("__typename") or "Unknown"
            if content_type == "Issue":
                number = content.get("number")
                owner = content.get("repository")
                if (
                    isinstance(number, bool)
                    or not isinstance(number, int)
                    or number < 1
                    or not isinstance(owner, dict)
                    or not isinstance(owner.get("nameWithOwner"), str)
                ):
                    raise ProjectSyncApiError("API_PARTIAL_RESPONSE")
                # 別 repository の Issue は本 snapshot に載りえないので、
                # ref を作らず「Issue 以外」と同じ対象外扱いにする。
                if owner["nameWithOwner"] == repository:
                    issue_ref = f"{repository}#{number}"
        value = raw.get("fieldValueByName")
        status: str | None = None
        if value is not None:
            if (
                not isinstance(value, dict)
                or value.get("__typename") != "ProjectV2ItemFieldSingleSelectValue"
            ):
                raise ProjectSyncApiError("API_PARTIAL_RESPONSE")
            name = value.get("name")
            if name is not None and (not isinstance(name, str) or not name):
                raise ProjectSyncApiError("API_PARTIAL_RESPONSE")
            status = name
        return ProjectItem(
            item_id=raw["id"],
            issue_ref=issue_ref,
            status=status,
            content_type=content_type,
        )

    def fetch_project(
        self, project_id: str, repository: str, expected_number: int | None = None
    ) -> ProjectView:
        cursor: str | None = None
        seen: set[str | None] = set()
        items: list[ProjectItem] = []
        field_id: str | None = None
        options: dict[str, str] = {}
        number: int | None = None
        title = ""
        while True:
            if cursor in seen:
                raise ProjectSyncApiError("PAGINATION_INCOMPLETE")
            seen.add(cursor)
            data = self._graphql(_PROJECT_QUERY, {"project": project_id, "cursor": cursor})
            node = data.get("node")
            if not isinstance(node, dict) or node.get("__typename") != "ProjectV2":
                raise ProjectSyncApiError("PROJECT_NOT_FOUND")
            if node.get("id") != project_id:
                raise ProjectSyncApiError("IDENTITY_MISMATCH")
            page_number = node.get("number")
            if isinstance(page_number, bool) or not isinstance(page_number, int):
                raise ProjectSyncApiError("API_PARTIAL_RESPONSE")
            if number is None:
                number = page_number
                title = node.get("title") if isinstance(node.get("title"), str) else ""
                field_id, options = self._status_field(node.get("field"))
            elif number != page_number:
                raise ProjectSyncApiError("IDENTITY_MISMATCH")
            connection = node.get("items")
            if (
                not isinstance(connection, dict)
                or not isinstance(connection.get("nodes"), list)
                or not isinstance(connection.get("pageInfo"), dict)
            ):
                raise ProjectSyncApiError("API_PARTIAL_RESPONSE")
            for raw in connection["nodes"]:
                items.append(self._item(raw, repository))
            page = connection["pageInfo"]
            if not isinstance(page.get("hasNextPage"), bool):
                raise ProjectSyncApiError("API_PARTIAL_RESPONSE")
            if not page["hasNextPage"]:
                break
            cursor = page.get("endCursor")
            if not isinstance(cursor, str) or not cursor:
                raise ProjectSyncApiError("PAGINATION_INCOMPLETE")
        if field_id is None or number is None:
            raise ProjectSyncApiError("STATUS_FIELD_UNREADABLE")
        if expected_number is not None and expected_number != number:
            raise ProjectSyncApiError("IDENTITY_MISMATCH")
        item_ids = {item.item_id for item in items}
        if len(item_ids) != len(items):
            raise ProjectSyncApiError("IDENTITY_MISMATCH")
        return ProjectView(
            project_id=project_id,
            number=number,
            title=title,
            status_field_id=field_id,
            status_option_ids=options,
            items=tuple(items),
        )

    def set_status(
        self, project_id: str, item_id: str, field_id: str, option_id: str
    ) -> None:
        data = self._graphql(
            _UPDATE_MUTATION,
            {"project": project_id, "item": item_id, "field": field_id, "option": option_id},
        )
        payload = data.get("updateProjectV2ItemFieldValue")
        item = payload.get("projectV2Item") if isinstance(payload, dict) else None
        if not isinstance(item, dict) or item.get("id") != item_id:
            raise ProjectSyncApiError("IDENTITY_MISMATCH")
