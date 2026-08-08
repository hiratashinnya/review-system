"""Issue-start policy adapter。

blocker dependency と branch source は別 policy として評価し、この adapter が
managed dispatch の直前で両方の ALLOW を結合する。判定不能はすべて ERROR。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from blocker_gate.contract import ContractError, validate_result_semantics
from blocker_gate.github import GitHubCollector
from blocker_gate.resolver import evaluate_snapshot
from branch_source import (
    BranchSourceError,
    BranchSourceResult,
    GitHubBranchClient,
    NewBranchRequest,
    verify_branch_source,
)


ISSUE_START_POLICY_VERSION = "issue-start/1.0"
BINDING_MARKER = "ISSUE_START_BINDING_V1="
ENTRYPOINT_MANIFEST = Path(__file__).with_name("managed-entrypoints-v1.json")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_OID = re.compile(r"^[0-9a-f]{40}$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_BRANCH = _REF


class IssueStartError(Exception):
    """identity/contract/API を一意に検証できない fail-close error。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class IssueStartGitHubCollector(GitHubCollector):
    """resolver snapshot に加え、deny report 用の title/URL を fresh read する。"""

    def issue_metadata(self, repository: str, number: int) -> Mapping[str, Any]:
        value, _headers = self._get(f"/repos/{repository}/issues/{number}")
        if not isinstance(value, dict):
            raise IssueStartError("ISSUE_START_REPORT_API_PARTIAL")
        return value


@dataclass(frozen=True)
class IssueStartRequest:
    entrypoint: str
    repository: str
    issue: int
    branch_name: str
    base_ref: str
    base_oid: str
    base_pr: int | None = None


def _manifest() -> Mapping[str, Any]:
    try:
        raw = json.loads(ENTRYPOINT_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IssueStartError("ISSUE_START_MANIFEST_ERROR") from exc
    if not isinstance(raw, dict) or raw.get("policy_version") != ISSUE_START_POLICY_VERSION:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    return raw


def _request(raw: Mapping[str, Any]) -> IssueStartRequest:
    expected = {
        "entrypoint", "repository", "issue", "branch_name", "base_ref", "base_oid", "base_pr"
    }
    if set(raw) - expected:
        raise IssueStartError("ISSUE_START_BINDING_UNKNOWN_FIELD")
    entrypoint = raw.get("entrypoint")
    repository = raw.get("repository")
    issue = raw.get("issue")
    branch_name = raw.get("branch_name")
    base_ref = raw.get("base_ref")
    base_oid = raw.get("base_oid")
    base_pr = raw.get("base_pr")
    if not isinstance(entrypoint, str):
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN")
    managed = _manifest().get("managed")
    if not isinstance(managed, list) or entrypoint not in {
        item.get("entrypoint") for item in managed if isinstance(item, dict)
    }:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", entrypoint)
    if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise IssueStartError("ISSUE_START_REPOSITORY_INVALID")
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise IssueStartError("ISSUE_START_ISSUE_INVALID")
    if not isinstance(branch_name, str) or not _BRANCH.fullmatch(branch_name):
        raise IssueStartError("ISSUE_START_BRANCH_INVALID")
    if not isinstance(base_ref, str) or not _REF.fullmatch(base_ref):
        raise IssueStartError("ISSUE_START_BASE_REF_INVALID")
    if not isinstance(base_oid, str) or not _OID.fullmatch(base_oid):
        raise IssueStartError("ISSUE_START_BASE_OID_INVALID")
    if base_pr is not None and (
        not isinstance(base_pr, int) or isinstance(base_pr, bool) or base_pr < 1
    ):
        raise IssueStartError("ISSUE_START_BASE_PR_INVALID")
    return IssueStartRequest(
        entrypoint, repository, issue, branch_name, base_ref, base_oid, base_pr
    )


def parse_dispatch_payload(payload: Mapping[str, Any]) -> IssueStartRequest | None:
    """Codex/Claude の tool payload から managed dispatch binding を読む。

    issue-implementer 以外は manifest 上の unmanaged operation なので対象外。
    issue-implementer は marker 欠如・重複・tool mismatch をすべて拒否する。
    """
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        raise IssueStartError("ISSUE_START_PAYLOAD_INVALID")
    agent_type = tool_input.get("agent_type", tool_input.get("subagent_type"))
    if not isinstance(agent_type, str) or not agent_type:
        raise IssueStartError("ISSUE_START_TARGET_UNKNOWN")
    if agent_type != "issue-implementer":
        return None
    leaf_tool = tool_name.rsplit(".", 1)[-1]
    if leaf_tool not in {"spawn_agent", "Task"}:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", tool_name)
    prompt = tool_input.get("message", tool_input.get("prompt"))
    if not isinstance(prompt, str):
        raise IssueStartError("ISSUE_START_BINDING_MISSING")
    lines = [line for line in prompt.splitlines() if line.startswith(BINDING_MARKER)]
    if len(lines) != 1:
        raise IssueStartError("ISSUE_START_BINDING_MISSING_OR_DUPLICATE")
    try:
        raw = json.loads(lines[0][len(BINDING_MARKER):])
    except json.JSONDecodeError as exc:
        raise IssueStartError("ISSUE_START_BINDING_INVALID_JSON") from exc
    if not isinstance(raw, dict):
        raise IssueStartError("ISSUE_START_BINDING_INVALID_JSON")
    return _request(raw)


def _error_evidence(request: IssueStartRequest | None, reason: str, detail: str = "") -> dict[str, Any]:
    return {
        "schema_version": "issue-start-evidence/1",
        "policy_version": ISSUE_START_POLICY_VERSION,
        "result": "ERROR",
        "exit_code": 20,
        "reason": reason,
        "detail": detail,
        "binding": asdict(request) if request is not None else None,
        "blocker_evidence": None,
        "branch_source_evidence": None,
        "blockers": [],
    }


def _blocker_report(collector: Any, blocker: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not hasattr(collector, "issue_metadata"):
        raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
    report: list[dict[str, Any]] = []
    seen: set[str] = set()
    for finding in blocker.get("findings", []):
        if finding.get("code") != "OPEN_BLOCKER" or finding.get("waiver_id") is not None:
            continue
        path = finding.get("path")
        if not isinstance(path, list) or not path or not isinstance(path[-1], str):
            raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
        blocker_ref = path[-1]
        if "#" not in blocker_ref:
            raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
        repository, raw_number = blocker_ref.rsplit("#", 1)
        if not raw_number.isdigit():
            raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
        if blocker_ref in seen:
            continue
        seen.add(blocker_ref)
        try:
            metadata = collector.issue_metadata(repository, int(raw_number))
        except IssueStartError:
            raise
        except Exception as exc:
            raise IssueStartError("ISSUE_START_REPORT_API_ERROR", type(exc).__name__) from exc
        title = metadata.get("title")
        url = metadata.get("html_url")
        if not isinstance(title, str) or not title or not isinstance(url, str) or not url:
            raise IssueStartError("ISSUE_START_REPORT_API_PARTIAL")
        report.append({
            "number": int(raw_number),
            "repository": repository,
            "title": title,
            "url": url,
            "path": path,
            "next_action": "blockerをcloseするかblocking relationを解消し、fresh invocationで再試行する",
        })
    return report


def evaluate_issue_start(
    request: IssueStartRequest,
    *,
    cwd: Path | None = None,
    collector_factory: Callable[[str | None], Any] = IssueStartGitHubCollector,
    branch_api_factory: Callable[[str | None], Any] = GitHubBranchClient,
    token: str | None = None,
    branch_verifier: Callable[..., BranchSourceResult] = verify_branch_source,
) -> dict[str, Any]:
    """fresh blocker read を先に行い、ALLOW 後だけ base policy を検証する。"""
    try:
        collector = collector_factory(token)
        # #299 完了前は waiver provider を渡さない。collector に機能があっても bypass 不可。
        blocker = evaluate_snapshot(
            collector.collect_issue(request.repository, request.issue),
            waiver_provider=None,
        )
        validate_result_semantics(blocker, int(blocker["exit_code"]))
        subject = blocker.get("subject")
        if (
            blocker.get("mode") != "issue-start"
            or blocker.get("repository") != request.repository
            or not isinstance(subject, dict)
            or subject.get("type") != "issue"
            or subject.get("number") != request.issue
        ):
            raise IssueStartError("ISSUE_START_BLOCKER_BINDING_MISMATCH")
        if blocker["result"] != "ALLOW":
            blockers = _blocker_report(collector, blocker) if blocker["result"] == "BLOCK" else []
            return {
                "schema_version": "issue-start-evidence/1",
                "policy_version": ISSUE_START_POLICY_VERSION,
                "result": blocker["result"],
                "exit_code": blocker["exit_code"],
                "reason": blocker["primary_reason"],
                "fetched_at": blocker["fetched_at"],
                "binding": asdict(request),
                "blocker_evidence": blocker,
                "branch_source_evidence": None,
                "blockers": blockers,
            }
        source = branch_verifier(
            NewBranchRequest(
                request.branch_name,
                request.repository,
                request.base_ref,
                request.base_oid,
                request.base_pr,
            ),
            cwd=cwd,
            api=branch_api_factory(token),
        )
        return {
            "schema_version": "issue-start-evidence/1",
            "policy_version": ISSUE_START_POLICY_VERSION,
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
            "fetched_at": blocker["fetched_at"],
            "binding": asdict(request),
            "blocker_evidence": blocker,
            "branch_source_evidence": asdict(source),
            "blockers": [],
        }
    except IssueStartError:
        raise
    except ContractError as exc:
        raise IssueStartError("ISSUE_START_CONTRACT_ERROR", str(exc)) from exc
    except BranchSourceError as exc:
        raise IssueStartError(exc.reason, exc.detail) from exc
    except Exception as exc:
        raise IssueStartError("ISSUE_START_EVALUATION_ERROR", type(exc).__name__) from exc


def fail_closed(request: IssueStartRequest | None, exc: IssueStartError) -> dict[str, Any]:
    return _error_evidence(request, exc.reason, exc.detail)
