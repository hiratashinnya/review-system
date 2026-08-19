"""``adopt-branch``: 既存ブランチを worktree 側で checkout する（Issue #354・PR-2・FR-W10）。

**なぜ ``new-branch`` と別 verb なのか**
------------------------------------
``branch_source.policy`` の :func:`verify_branch_source` / :func:`create_branch` は
「**新規**ブランチをどこから生やすか」を fresh evidence へ束縛する流れで、分岐点が
「default branch の先端」か「same-repository の OPEN PR の head」かの二分岐になっている。
``adopt-branch`` が解くのは別の問題——**既に存在するブランチ**（前ラウンドの
``issue-implementer`` が push 済みのもの）を、新しく切り出した worktree の中で
「本当に自分が想定している OID か」を確かめてから checkout することである。
分岐点の二分岐は無く、代わりに「remote の先端が期待 OID と一致するか」「（任意で）その OID が
指定 PR の head として open か」「ローカルに同名ブランチが無いか」を見る。

したがって本モジュールは ``policy.py`` のフローをコピー流用せず、**必要な部分だけを薄く
再実装**する。ただし leaf 値（repository/branch/OID）の検証規則を二重定義すると
「片方だけ緩い」というズレが生まれるため、そこは ``branch_source`` の公開 validator を共有する。
read-only の GitHub client（:class:`GitHubBranchClient`）もそのまま再利用する。

fail-close
----------
引数検証・remote 検証・PR 検証・ローカル衝突検査の**いずれか1つでも欠ければ git を実行しない**
（``git switch`` に到達するのは全段を通過したときだけ）。API へ到達できない場合も
``API_UNREACHABLE`` で fail-close する（「確認できなかった」を「問題なし」に潰さない）。

reason code:
  * ``BRANCH_ARGUMENT_INVALID`` / ``BRANCH_NAME_INVALID`` / ``BRANCH_REPOSITORY_INVALID``
  * ``BRANCH_ADOPT_OID_INVALID`` / ``BRANCH_ADOPT_PR_INVALID``（引数スキーマ）
  * ``BRANCH_ADOPT_REMOTE_MISSING``（``origin/<branch>`` が解決できない）
  * ``BRANCH_ADOPT_OID_MISMATCH``（remote 先端が期待 OID と違う）
  * ``BRANCH_ADOPT_PR_NOT_OPEN`` / ``BRANCH_ADOPT_PR_HEAD_MISMATCH``（PR 再検証）
  * ``API_UNREACHABLE`` / ``API_UNAVAILABLE``（``GitHubBranchClient`` 由来）
  * ``BRANCH_ADOPT_LOCAL_EXISTS``（ローカルに同名ブランチが既にある）
  * ``BRANCH_ADOPT_ALREADY_CHECKED_OUT``（別 worktree が同じブランチを掴んでいる）

依存仕様:
  * ``branch_source/policy.py`` の :class:`BranchSourceError` / :class:`GitHubBranchClient` /
    公開 leaf validator（同一 PR で公開名を追加）。
  * 起票先区分は `.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」の
    **汎用開発ハーネス**（Issue 運用パイプライン）。out-of-graph のため版なし。
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from blocker_gate.auth import resolve_github_token
from branch_source.policy import (
    BranchApi,
    BranchSourceError,
    GitHubBranchClient,
    validate_branch_ref,
    validate_repository,
)

ADOPT_POLICY_VERSION = "branch-adopt/1.0"

# adopt は「その worktree が掴む commit」を一意に固定するのが目的なので、abbrev も 64hex も
# 受け付けない（40hex の full OID ちょうど）。
_ADOPT_OID = re.compile(r"^[0-9a-f]{40}$")
_POSITIVE_INT = re.compile(r"^[1-9][0-9]*$")

# git が「そのブランチは別 worktree が使用中」を伝えるときの文言（バージョン差を吸収するため
# 部分一致の集合で持つ。ここに無い文言なら汎用の BRANCH_GIT_ERROR に落ちるだけで fail-open しない）。
_ALREADY_CHECKED_OUT_MARKERS = (
    "already checked out",
    "already used by worktree",
    "is already used by worktree",
)


@dataclass(frozen=True)
class AdoptBranchRequest:
    branch_name: str
    repository: str
    expected_oid: str
    pr: int | None = None


@dataclass(frozen=True)
class AdoptBranchResult:
    branch_name: str
    repository: str
    expected_oid: str
    pr: int | None
    policy_version: str = ADOPT_POLICY_VERSION


def parse_adopt_branch_args(args: Sequence[str]) -> AdoptBranchRequest:
    """固定 schema の adopt-branch 引数を parse する。未知/重複 flag は拒否（git は実行しない）。"""
    if not args:
        raise BranchSourceError("BRANCH_ARGUMENT_INVALID", "missing branch name")
    name = validate_branch_ref(args[0], "BRANCH_NAME_INVALID")
    values: dict[str, str] = {}
    allowed = {"--repository", "--expected-oid", "--pr"}
    index = 1
    while index < len(args):
        flag = args[index]
        if flag not in allowed or flag in values or index + 1 >= len(args):
            raise BranchSourceError("BRANCH_ARGUMENT_INVALID", flag)
        values[flag] = args[index + 1]
        index += 2
    required = {"--repository", "--expected-oid"}
    if not required.issubset(values):
        missing = ",".join(sorted(required - set(values)))
        raise BranchSourceError("BRANCH_ARGUMENT_INVALID", f"missing {missing}")

    raw_oid = values["--expected-oid"]
    normalized_oid = raw_oid.lower()
    if not _ADOPT_OID.fullmatch(normalized_oid):
        raise BranchSourceError("BRANCH_ADOPT_OID_INVALID", raw_oid)

    pr: int | None = None
    if "--pr" in values:
        raw_pr = values["--pr"]
        if not _POSITIVE_INT.fullmatch(raw_pr):
            raise BranchSourceError("BRANCH_ADOPT_PR_INVALID", raw_pr)
        pr = int(raw_pr)

    return AdoptBranchRequest(
        branch_name=name,
        repository=validate_repository(values["--repository"]),
        expected_oid=normalized_oid,
        pr=pr,
    )


def _run_git(
    argv: Sequence[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess],
) -> subprocess.CompletedProcess:
    return runner(list(argv), cwd=str(cwd), text=True, capture_output=True, shell=False)


def _require_ok(
    completed: subprocess.CompletedProcess, reason: str, detail: str = ""
) -> str:
    if completed.returncode != 0:
        raise BranchSourceError(reason, detail)
    return (completed.stdout or "").strip()


def _string_at(raw: Mapping[str, Any], *path: str) -> str:
    value: Any = raw
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE", "/".join(path))
        value = value[key]
    if not isinstance(value, str) or not value:
        raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE", "/".join(path))
    return value


def _verify_pull_request(
    request: AdoptBranchRequest, *, api: BranchApi
) -> None:
    """``--pr`` 指定時、その PR が open かつ head が期待 OID/ブランチであることを再検証する。

    remote 先端の OID 一致だけだと「その OID が今も PR の head である」ことは言えない
    （force-push や PR クローズの直後を掴みうる）。到達不能は :class:`BranchSourceError`
    （``API_UNREACHABLE``）として client 側から送出され、ここで握り潰さない＝fail-close。
    """
    pull = api.pull_request(request.repository, int(request.pr))
    if not isinstance(pull, dict):
        raise BranchSourceError("BRANCH_API_PARTIAL_RESPONSE", "pull_request")
    if pull.get("state") != "open":
        raise BranchSourceError("BRANCH_ADOPT_PR_NOT_OPEN", str(request.pr))
    head_ref = _string_at(pull, "head", "ref")
    head_sha = _string_at(pull, "head", "sha").lower()
    if head_ref != request.branch_name:
        raise BranchSourceError(
            "BRANCH_ADOPT_PR_HEAD_MISMATCH", f"head.ref={head_ref}"
        )
    if head_sha != request.expected_oid:
        raise BranchSourceError(
            "BRANCH_ADOPT_PR_HEAD_MISMATCH", f"head.sha={head_sha}"
        )


def adopt_branch(
    request: AdoptBranchRequest,
    *,
    cwd: Path | None = None,
    api: BranchApi | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> AdoptBranchResult:
    """既存ブランチを検証済み exact OID で checkout する（全段 fail-close）。"""
    workdir = Path.cwd() if cwd is None else cwd

    # 1. fresh fetch（判定材料をローカルの古い ref に依存させない）。
    _require_ok(
        _run_git(["git", "fetch", "--prune", "origin"], cwd=workdir, runner=runner),
        "BRANCH_GIT_ERROR",
        "fetch",
    )

    # 2. remote 先端 == 期待 OID。
    remote_ref = f"refs/remotes/origin/{request.branch_name}"
    observed = _require_ok(
        _run_git(
            ["git", "rev-parse", "--verify", f"{remote_ref}^{{commit}}"],
            cwd=workdir,
            runner=runner,
        ),
        "BRANCH_ADOPT_REMOTE_MISSING",
        remote_ref,
    ).lower()
    if not _ADOPT_OID.fullmatch(observed):
        raise BranchSourceError("BRANCH_ADOPT_REMOTE_OID_INVALID", observed)
    if observed != request.expected_oid:
        raise BranchSourceError(
            "BRANCH_ADOPT_OID_MISMATCH",
            f"expected {request.expected_oid}; observed {observed}",
        )

    # 3. PR head の再検証（任意）。
    if request.pr is not None:
        client = api or GitHubBranchClient(resolve_github_token())
        _verify_pull_request(request, api=client)

    # 4. ローカル同名ブランチの不在。isolated worktree は毎回まっさらなので、
    #    存在する＝想定外の状態（前回の残骸 or 別 dispatch の混線）＝止める。
    local_ref = f"refs/heads/{request.branch_name}"
    local = _run_git(
        ["git", "rev-parse", "--verify", "--quiet", local_ref],
        cwd=workdir,
        runner=runner,
    )
    if local.returncode == 0:
        raise BranchSourceError("BRANCH_ADOPT_LOCAL_EXISTS", request.branch_name)

    # 5. checkout（検証済み exact OID を明示。current HEAD を暗黙継承しない）。
    switched = _run_git(
        ["git", "switch", "--create", request.branch_name, request.expected_oid],
        cwd=workdir,
        runner=runner,
    )
    if switched.returncode != 0:
        stderr = (switched.stderr or "").lower()
        if any(marker in stderr for marker in _ALREADY_CHECKED_OUT_MARKERS):
            raise BranchSourceError(
                "BRANCH_ADOPT_ALREADY_CHECKED_OUT",
                f"{request.branch_name}（先行 worktree を `python3 -m gitgate collect-worktree` "
                "で解放してから再実行する）",
            )
        raise BranchSourceError("BRANCH_GIT_ERROR", "switch")

    # 6. upstream 束縛（以後の push/status が origin/<branch> を基準に読める）。
    _require_ok(
        _run_git(
            [
                "git",
                "branch",
                f"--set-upstream-to=origin/{request.branch_name}",
                request.branch_name,
            ],
            cwd=workdir,
            runner=runner,
        ),
        "BRANCH_GIT_ERROR",
        "set-upstream",
    )

    return AdoptBranchResult(
        branch_name=request.branch_name,
        repository=request.repository,
        expected_oid=request.expected_oid,
        pr=request.pr,
    )
