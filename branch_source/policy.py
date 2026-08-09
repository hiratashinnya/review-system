"""Issue #317: new-branch の分岐元を fresh remote evidence で検証する。

blocker dependency の判定とは材料も失敗理由も異なるため、`blocker_gate`
には混ぜない。通常 branch は fresh `origin/<default>`、stacked branch は
明示された same-repository OPEN PR の exact head OID だけを許可する。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence


API_VERSION = "2022-11-28"
POLICY_VERSION = "branch-source/1.0"
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")
_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_HTTPS_REMOTE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")
_SSH_REMOTE = re.compile(r"^(?:git@github\.com:|ssh://git@github\.com/)([^/]+)/([^/]+?)(?:\.git)?/?$")


class BranchSourceError(Exception):
    """分岐元を一意かつ fresh に証明できない場合の fail-close error。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class NewBranchRequest:
    branch_name: str
    repository: str
    base_ref: str
    base_oid: str
    base_pr: int | None = None


@dataclass(frozen=True)
class BranchSourceResult:
    repository: str
    default_branch: str
    source_oid: str
    source_kind: str
    base_pr: int | None
    policy_version: str = POLICY_VERSION


class BranchApi(Protocol):
    def repository(self, repository: str) -> Mapping[str, Any]: ...

    def pull_request(self, repository: str, number: int) -> Mapping[str, Any]: ...


class GitHubBranchClient:
    """GitHub standard REST API の read-only client（外部 SaaS 不使用）。"""

    def __init__(self, token: str | None = None) -> None:
        self._headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "review-system-branch-source/1.0",
        }
        if token:
            self._headers["Authorization"] = "Bearer " + token

    def _get(self, path: str) -> Mapping[str, Any]:
        request = urllib.request.Request(
            "https://api.github.com" + path,
            headers=self._headers,
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403, 404}:
                raise BranchSourceError("BRANCH_API_PERMISSION_OR_NOT_FOUND") from exc
            raise BranchSourceError("BRANCH_API_ERROR", f"HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BranchSourceError("BRANCH_API_ERROR", type(exc).__name__) from exc
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE") from exc
        if not isinstance(value, dict):
            raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE")
        return value

    def repository(self, repository: str) -> Mapping[str, Any]:
        return self._get(f"/repos/{repository}")

    def pull_request(self, repository: str, number: int) -> Mapping[str, Any]:
        return self._get(f"/repos/{repository}/pulls/{number}")


def _validate_repository(value: str) -> str:
    if not _REPOSITORY.fullmatch(value):
        raise BranchSourceError("BRANCH_REPOSITORY_INVALID", value)
    return value


def _validate_branch(value: str, reason: str) -> str:
    if (
        not value
        or value.startswith(("-", "/"))
        or value.endswith(("/", "."))
        or not _BRANCH.fullmatch(value)
        or ".." in value
        or "//" in value
        or "@{" in value
        or any(
            not part or part.startswith(".") or part.endswith(".lock")
            for part in value.split("/")
        )
    ):
        raise BranchSourceError(reason, value)
    return value


def _validate_oid(value: str, reason: str = "BRANCH_BASE_OID_INVALID") -> str:
    normalized = value.lower()
    if not _OID.fullmatch(normalized):
        raise BranchSourceError(reason, value)
    return normalized


def parse_new_branch_args(args: Sequence[str]) -> NewBranchRequest:
    """固定 schema の new-branch 引数を parse する。未知/重複 flag は拒否。"""
    if not args:
        raise BranchSourceError("BRANCH_ARGUMENT_INVALID", "missing branch name")
    name = _validate_branch(args[0], "BRANCH_NAME_INVALID")
    values: dict[str, str] = {}
    allowed = {"--repository", "--base-ref", "--base-oid", "--base-pr"}
    index = 1
    while index < len(args):
        flag = args[index]
        if flag not in allowed or flag in values or index + 1 >= len(args):
            raise BranchSourceError("BRANCH_ARGUMENT_INVALID", flag)
        values[flag] = args[index + 1]
        index += 2
    required = {"--repository", "--base-ref", "--base-oid"}
    if not required.issubset(values):
        missing = ",".join(sorted(required - set(values)))
        raise BranchSourceError("BRANCH_ARGUMENT_INVALID", f"missing {missing}")
    base_pr: int | None = None
    if "--base-pr" in values:
        raw_pr = values["--base-pr"]
        if not raw_pr.isdigit() or int(raw_pr) < 1:
            raise BranchSourceError("BRANCH_BASE_PR_INVALID", raw_pr)
        base_pr = int(raw_pr)
    return NewBranchRequest(
        branch_name=name,
        repository=_validate_repository(values["--repository"]),
        base_ref=_validate_branch(values["--base-ref"], "BRANCH_BASE_REF_INVALID"),
        base_oid=_validate_oid(values["--base-oid"]),
        base_pr=base_pr,
    )


def _remote_repository(remote_url: str) -> str:
    for pattern in (_HTTPS_REMOTE, _SSH_REMOTE):
        match = pattern.fullmatch(remote_url.strip())
        if match:
            return _validate_repository(f"{match.group(1)}/{match.group(2)}")
    raise BranchSourceError("BRANCH_REMOTE_AMBIGUOUS")


def _run_git(
    argv: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    completed = runner(
        list(argv),
        cwd=str(cwd),
        text=True,
        capture_output=True,
        shell=False,
    )
    if completed.returncode != 0:
        raise BranchSourceError("BRANCH_GIT_ERROR", argv[1] if len(argv) > 1 else "git")
    return completed.stdout.strip()


def _nested_string(raw: Mapping[str, Any], *path: str) -> str:
    value: Any = raw
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE")
        value = value[key]
    if not isinstance(value, str) or not value:
        raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE")
    return value


def _pull_head_oid(pull: Mapping[str, Any], repository: str) -> str:
    """stacked PR の open/same-repository/head binding を閉じて読む。"""
    if pull.get("state") != "open":
        raise BranchSourceError("BRANCH_BASE_PR_NOT_OPEN")
    head_repo = _nested_string(pull, "head", "repo", "full_name")
    base_repo = _nested_string(pull, "base", "repo", "full_name")
    if head_repo.lower() != repository.lower() or base_repo.lower() != repository.lower():
        raise BranchSourceError("BRANCH_BASE_PR_CROSS_REPOSITORY")
    return _validate_oid(
        _nested_string(pull, "head", "sha"), "BRANCH_PR_HEAD_OID_INVALID"
    )


def verify_branch_source(
    request: NewBranchRequest,
    *,
    cwd: Path | None = None,
    api: BranchApi | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> BranchSourceResult:
    """fresh API/git evidence で分岐元を検証する（branch は作らない）。"""
    workdir = Path.cwd() if cwd is None else cwd
    remote_url = _run_git(["git", "remote", "get-url", "origin"], cwd=workdir, runner=runner)
    if _remote_repository(remote_url).lower() != request.repository.lower():
        raise BranchSourceError("BRANCH_REPOSITORY_MISMATCH")

    client = api or GitHubBranchClient(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    repository_data = client.repository(request.repository)
    full_name = _nested_string(repository_data, "full_name")
    default_branch = _validate_branch(
        _nested_string(repository_data, "default_branch"),
        "BRANCH_DEFAULT_REF_INVALID",
    )
    if full_name.lower() != request.repository.lower():
        raise BranchSourceError("BRANCH_REPOSITORY_MISMATCH")
    if default_branch != request.base_ref:
        raise BranchSourceError("BRANCH_DEFAULT_REF_MISMATCH")

    if request.base_pr is None:
        local_ref = "refs/review-system/branch-source/default"
        refspec = f"+refs/heads/{default_branch}:{local_ref}"
        _run_git(
            ["git", "fetch", "--force", "--no-tags", "origin", refspec],
            cwd=workdir,
            runner=runner,
        )
        observed = _validate_oid(
            _run_git(
                ["git", "rev-parse", "--verify", f"{local_ref}^{{commit}}"],
                cwd=workdir,
                runner=runner,
            ),
            "BRANCH_REMOTE_OID_INVALID",
        )
        if observed != request.base_oid:
            raise BranchSourceError("BRANCH_BASE_OID_MISMATCH")
        source_kind = "default-branch"
    else:
        pull_before = client.pull_request(request.repository, request.base_pr)
        head_oid = _pull_head_oid(pull_before, request.repository)
        if head_oid != request.base_oid:
            raise BranchSourceError("BRANCH_BASE_OID_MISMATCH")
        local_pr_ref = f"refs/remotes/origin/review-system-pr/{request.base_pr}"
        refspec = f"+refs/pull/{request.base_pr}/head:{local_pr_ref}"
        _run_git(
            ["git", "fetch", "--force", "--no-tags", "origin", refspec],
            cwd=workdir,
            runner=runner,
        )
        pull_after = client.pull_request(request.repository, request.base_pr)
        rebound_oid = _pull_head_oid(pull_after, request.repository)
        if rebound_oid != head_oid:
            raise BranchSourceError("BRANCH_BASE_PR_CHANGED")
        observed = _validate_oid(
            _run_git(
                ["git", "rev-parse", "--verify", f"{local_pr_ref}^{{commit}}"],
                cwd=workdir,
                runner=runner,
            ),
            "BRANCH_REMOTE_OID_INVALID",
        )
        if observed != rebound_oid:
            raise BranchSourceError("BRANCH_PR_HEAD_MISMATCH")
        source_kind = "same-repository-open-pr"

    return BranchSourceResult(
        repository=request.repository,
        default_branch=default_branch,
        source_oid=request.base_oid,
        source_kind=source_kind,
        base_pr=request.base_pr,
    )


def create_branch(
    request: NewBranchRequest,
    *,
    cwd: Path | None = None,
    api: BranchApi | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> BranchSourceResult:
    """検証済み exact OID を明示して branch を作成する。"""
    workdir = Path.cwd() if cwd is None else cwd
    result = verify_branch_source(request, cwd=workdir, api=api, runner=runner)
    _run_git(
        ["git", "switch", "-c", request.branch_name, result.source_oid],
        cwd=workdir,
        runner=runner,
    )
    return result
