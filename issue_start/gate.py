"""Managed Issue dispatch 直前の blocker policy adapter。

Codex は暗号化される prompt を binding に使わず、平文 task_name と
hook 実行 worktree から Issue/repository を一意に導く。Claude は既存の
prompt marker 契約を維持する。branch-source policy は ``gitgate new-branch`` の
独立 gate であり、dispatch 直前の blocker 判定には混ぜない。
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from blocker_gate.contract import ContractError, validate_result_semantics
from blocker_gate.github import GitHubCollector
from blocker_gate.resolver import evaluate_snapshot


ISSUE_START_POLICY_VERSION = "issue-start/1.0"
BINDING_MARKER = "ISSUE_START_BINDING_V1="
ENTRYPOINT_MANIFEST = Path(__file__).with_name("managed-entrypoints-v1.json")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_OID = re.compile(r"^[0-9a-f]{40}$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_BRANCH = _REF
_HTTPS_REMOTE = re.compile(
    r"^https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/"
    r"([A-Za-z0-9_.-]{1,100}?)(?:\.git)?$"
)
_SSH_REMOTE = re.compile(
    r"^(?:git@github\.com:|ssh://git@github\.com/)"
    r"([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100}?)(?:\.git)?$"
)


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


def _manifest() -> Mapping[str, Any]:
    try:
        raw = json.loads(ENTRYPOINT_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IssueStartError("ISSUE_START_MANIFEST_ERROR") from exc
    if not isinstance(raw, dict) or raw.get("policy_version") != ISSUE_START_POLICY_VERSION:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    return raw


def _managed_entries() -> list[Mapping[str, Any]]:
    managed = _manifest().get("managed")
    if not isinstance(managed, list) or not managed or not all(
        isinstance(item, dict) for item in managed
    ):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    return managed


def _request(raw: Mapping[str, Any]) -> IssueStartRequest:
    expected = {"entrypoint", "repository", "issue"}
    if set(raw) != expected:
        raise IssueStartError("ISSUE_START_BINDING_UNKNOWN_FIELD")
    entrypoint = raw.get("entrypoint")
    repository = raw.get("repository")
    issue = raw.get("issue")
    if not isinstance(entrypoint, str):
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN")
    if entrypoint not in {item.get("entrypoint") for item in _managed_entries()}:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", entrypoint)
    if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
        raise IssueStartError("ISSUE_START_REPOSITORY_INVALID")
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        raise IssueStartError("ISSUE_START_ISSUE_INVALID")
    return IssueStartRequest(entrypoint, repository, issue)


def _claude_request(raw: Mapping[str, Any]) -> IssueStartRequest:
    """Claude の既存 V1 marker schema を変えず、blocker binding だけを返す。"""
    expected = {
        "entrypoint", "repository", "issue", "branch_name", "base_ref", "base_oid", "base_pr"
    }
    if set(raw) != expected:
        raise IssueStartError("ISSUE_START_BINDING_UNKNOWN_FIELD")
    branch_name = raw.get("branch_name")
    base_ref = raw.get("base_ref")
    base_oid = raw.get("base_oid")
    base_pr = raw.get("base_pr")
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
    return _request({key: raw[key] for key in ("entrypoint", "repository", "issue")})


def _run_git(
    argv: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    try:
        completed = runner(
            list(argv), cwd=str(cwd), text=True, capture_output=True, shell=False
        )
    except OSError as exc:
        raise IssueStartError("ISSUE_START_GIT_ERROR", type(exc).__name__) from exc
    if completed.returncode != 0:
        raise IssueStartError("ISSUE_START_GIT_ERROR", argv[1] if len(argv) > 1 else "git")
    output = completed.stdout
    if not isinstance(output, str) or "\0" in output:
        raise IssueStartError("ISSUE_START_GIT_OUTPUT_INVALID")
    if output.endswith("\n"):
        output = output[:-1]
    if "\n" in output or "\r" in output:
        raise IssueStartError("ISSUE_START_GIT_OUTPUT_INVALID")
    return output


def _canonical_github_repository(remote_url: str) -> str:
    if "\n" in remote_url or "\r" in remote_url:
        raise IssueStartError("ISSUE_START_ORIGIN_INVALID")
    for pattern in (_HTTPS_REMOTE, _SSH_REMOTE):
        match = pattern.fullmatch(remote_url)
        if match:
            repository = f"{match.group(1)}/{match.group(2)}"
            if _REPOSITORY.fullmatch(repository):
                return repository
    raise IssueStartError("ISSUE_START_ORIGIN_INVALID")


def _codex_repository(
    payload: Mapping[str, Any],
    *,
    cwd: Path | None,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    payload_cwd = payload.get("cwd")
    if not isinstance(payload_cwd, str) or not payload_cwd or not Path(payload_cwd).is_absolute():
        raise IssueStartError("ISSUE_START_CWD_INVALID")
    try:
        payload_root = Path(payload_cwd).resolve(strict=True)
        hook_root = (Path.cwd() if cwd is None else cwd).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise IssueStartError("ISSUE_START_CWD_INVALID") from exc
    if not payload_root.is_dir() or payload_root != hook_root:
        raise IssueStartError("ISSUE_START_CWD_MISMATCH")
    if _run_git(["git", "rev-parse", "--is-inside-work-tree"], cwd=hook_root, runner=runner) != "true":
        raise IssueStartError("ISSUE_START_NOT_WORKTREE")
    top_level = _run_git(
        ["git", "rev-parse", "--show-toplevel"], cwd=hook_root, runner=runner
    )
    try:
        git_root = Path(top_level).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise IssueStartError("ISSUE_START_WORKTREE_ROOT_INVALID") from exc
    if git_root != hook_root:
        raise IssueStartError("ISSUE_START_WORKTREE_ROOT_MISMATCH")
    origin = _run_git(
        ["git", "remote", "get-url", "origin"], cwd=hook_root, runner=runner
    )
    return _canonical_github_repository(origin)


def _managed_transport(tool_name: str, agent_type: str) -> tuple[Mapping[str, Any], str, Mapping[str, Any]]:
    matches: list[tuple[Mapping[str, Any], str, Mapping[str, Any]]] = []
    for entry in _managed_entries():
        if entry.get("agent_type") != agent_type:
            continue
        transports = entry.get("binding_transports")
        if not isinstance(transports, dict):
            raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
        for harness, transport in transports.items():
            if not isinstance(harness, str) or not isinstance(transport, dict):
                raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
            tool_names = transport.get("tool_names")
            if not isinstance(tool_names, list) or not all(isinstance(name, str) for name in tool_names):
                raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
            if tool_name in tool_names:
                matches.append((entry, harness, transport))
    if not matches:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", tool_name)
    if len(matches) != 1:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_AMBIGUOUS", tool_name)
    return matches[0]


def parse_dispatch_payload(
    payload: Mapping[str, Any],
    *,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> IssueStartRequest | None:
    """Codex/Claude の tool payload から managed dispatch binding を読む。

    issue-implementer 以外は manifest 上の unmanaged operation なので対象外。
    issue-implementer は marker 欠如・重複・tool mismatch をすべて拒否する。
    """
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        raise IssueStartError("ISSUE_START_PAYLOAD_INVALID")
    targets = [tool_input.get(field) for field in ("agent_type", "subagent_type")]
    present_targets = [target for target in targets if target is not None]
    if len(present_targets) != 1 or not isinstance(present_targets[0], str) or not present_targets[0]:
        raise IssueStartError("ISSUE_START_TARGET_UNKNOWN")
    agent_type = present_targets[0]
    raw_managed_types = [item.get("agent_type") for item in _managed_entries()]
    if not all(isinstance(value, str) and value for value in raw_managed_types):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    managed_types = set(raw_managed_types)
    if agent_type not in managed_types:
        return None
    entry, harness, transport = _managed_transport(tool_name, agent_type)
    expected_field = transport.get("agent_type_field")
    if expected_field not in {"agent_type", "subagent_type"} or tool_input.get(expected_field) != agent_type:
        raise IssueStartError("ISSUE_START_TARGET_UNKNOWN")
    entrypoint = entry.get("entrypoint")
    if not isinstance(entrypoint, str):
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    if harness == "codex":
        task_name = tool_input.get("task_name")
        pattern = transport.get("task_name_pattern")
        if not isinstance(task_name, str) or not isinstance(pattern, str):
            raise IssueStartError("ISSUE_START_TASK_NAME_INVALID")
        try:
            match = re.fullmatch(pattern, task_name)
        except re.error as exc:
            raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR") from exc
        if match is None or match.lastindex != 1:
            raise IssueStartError("ISSUE_START_TASK_NAME_INVALID")
        issue = int(match.group(1))
        repository = _codex_repository(payload, cwd=cwd, runner=runner)
        return _request({"entrypoint": entrypoint, "repository": repository, "issue": issue})
    if harness != "claude":
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    prompt_field = transport.get("prompt_field")
    marker = transport.get("binding_marker")
    if not isinstance(prompt_field, str) or not isinstance(marker, str) or not marker:
        raise IssueStartError("ISSUE_START_MANIFEST_CONTRACT_ERROR")
    prompt = tool_input.get(prompt_field)
    if not isinstance(prompt, str):
        raise IssueStartError("ISSUE_START_BINDING_MISSING")
    lines = [line for line in prompt.splitlines() if line.startswith(marker)]
    if len(lines) != 1:
        raise IssueStartError("ISSUE_START_BINDING_MISSING_OR_DUPLICATE")
    try:
        raw = json.loads(lines[0][len(marker):])
    except json.JSONDecodeError as exc:
        raise IssueStartError("ISSUE_START_BINDING_INVALID_JSON") from exc
    if not isinstance(raw, dict):
        raise IssueStartError("ISSUE_START_BINDING_INVALID_JSON")
    request = _claude_request(raw)
    if request.entrypoint != entrypoint:
        raise IssueStartError("ISSUE_START_ENTRYPOINT_UNKNOWN", request.entrypoint)
    return request


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
    collector_factory: Callable[[str | None], Any] = IssueStartGitHubCollector,
    token: str | None = None,
) -> dict[str, Any]:
    """fresh blocker read を行い、同じ repository/Issue へ再束縛する。"""
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
                "blockers": blockers,
            }
        return {
            "schema_version": "issue-start-evidence/1",
            "policy_version": ISSUE_START_POLICY_VERSION,
            "result": "ALLOW",
            "exit_code": 0,
            "reason": "ISSUE_START_ALLOWED",
            "fetched_at": blocker["fetched_at"],
            "binding": asdict(request),
            "blocker_evidence": blocker,
            "blockers": [],
        }
    except IssueStartError:
        raise
    except ContractError as exc:
        raise IssueStartError("ISSUE_START_CONTRACT_ERROR", str(exc)) from exc
    except Exception as exc:
        raise IssueStartError("ISSUE_START_EVALUATION_ERROR", type(exc).__name__) from exc


def fail_closed(request: IssueStartRequest | None, exc: IssueStartError) -> dict[str, Any]:
    return _error_evidence(request, exc.reason, exc.detail)
