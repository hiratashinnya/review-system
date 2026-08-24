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
再実装**する。``repository`` と ``branch`` は検証規則を二重定義すると「片方だけ緩い」という
ズレが生まれるため、``branch_source`` の公開 validator（:func:`validate_repository` /
:func:`validate_branch_ref`）を共有する。read-only の GitHub client
（:class:`GitHubBranchClient`）もそのまま再利用する。

**OID だけは意図的に共有しない**。``branch_source`` 側は 40hex/64hex（SHA-1/SHA-256）の
どちらも受けるが、``adopt-branch`` は「その worktree が掴む commit を一意に固定する」ことが
目的なので ``_ADOPT_OID``（40hex ちょうど）で**より厳しく**判定する。ここで共有側の緩い規則に
揃えると adopt の目的が達成できないため、二重定義ではなく**意図的な非共有**である
（Issue #354 F-354-05）。

fail-close
----------
引数検証・remote 検証・PR 検証・ローカル衝突検査の**いずれか1つでも欠ければ git を実行しない**
（``git switch`` に到達するのは全段を通過したときだけ）。API へ到達できない場合も
``API_UNREACHABLE`` で fail-close する（「確認できなかった」を「問題なし」に潰さない）。

stage 4（ローカル同名ブランチの検査）の defense-in-depth（Issue #426）
------------------------------------------------------------------
``gitgate/worktree.py`` の ``worktree_release()`` は解放時に対応するローカルブランチ ref を
削除するが（``_cleanup_branch_ref``）、その削除はフェイルオープンであり、また
``worktree_release()`` を経由しない経路（旧版の実体・手動操作等）で残った stray ref も
ありうる。そのため stage 4 は「ローカル同名 ref があれば即 ``BRANCH_ADOPT_LOCAL_EXISTS``」
ではなく、まず**無害な残留 ref か本当の衝突かを判定**する：

1. ローカル ref の tip が ``refs/remotes/origin/<branch>`` の tip（stage 2 で検証済みの
   ``observed`` を再利用・再取得しない）と一致するか。
2. ``git worktree list --porcelain`` を見て、そのブランチが**いずれかの worktree**（main を
   含む・安全側）に checked out されていないか。

**両方を満たすときだけ**「無害な残留 ref」と判定し、``git branch -D`` で削除してから段5へ
進む（先行 worktree が既に消えている前提が壊れていないことを、削除の直前に確認している）。
**どちらか一方でも満たさなければ**（tip が食い違う＝別コミットを指すローカル作業／
``git worktree list`` が到達不能や異常終了＝判定不能／他 worktree が checked out 済み）
**既存どおり ``BRANCH_ADOPT_LOCAL_EXISTS`` で fail-close する**——未知のローカル作業を
黙って破棄しない。判定不能は「無害」ではなく「衝突」側に倒す（fail-close の一貫性）。
reclaim の ``git branch -D`` 自体が失敗した場合も同じ理由で fail-close する。

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
    公開 leaf validator（``validate_repository`` / ``validate_branch_ref``。同一 PR で公開名を
    追加。OID validator は上記のとおり共有しないので公開もしていない）。
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


def _branch_checked_out_elsewhere(
    branch_name: str, *, cwd: Path, runner: Callable[..., subprocess.CompletedProcess]
) -> bool:
    """``git worktree list --porcelain`` を見て、``branch_name`` がいずれかの worktree の
    HEAD として checked out されているかを判定する（main worktree も含める＝安全側）。

    到達不能・異常終了は「わからない」を「安全（checked out されていない）」に潰さず、
    checked out 済み扱い（``True``）にする——fail-close。stray ref の自動回収は「明確に
    無害と確認できたときだけ」行う契約なので、判定不能を無害側に倒さない。
    """
    completed = _run_git(
        ["git", "worktree", "list", "--porcelain"], cwd=cwd, runner=runner
    )
    if completed.returncode != 0:
        return True
    target = f"branch refs/heads/{branch_name}"
    for line in (completed.stdout or "").splitlines():
        if line.strip() == target:
            return True
    return False


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

    # 4. ローカル同名ブランチの検査。isolated worktree は毎回まっさらなので、存在する＝
    #    想定外の状態（前回の残骸 or 別 dispatch の混線）。ただし「無害な残留 ref」
    #    （``worktree_release()`` のブランチ削除がフェイルオープンで漏れた等）と
    #    「本当の衝突」を区別する（defense-in-depth・Issue #426・モジュール docstring参照）。
    local_ref = f"refs/heads/{request.branch_name}"
    local = _run_git(
        ["git", "rev-parse", "--verify", "--quiet", local_ref],
        cwd=workdir,
        runner=runner,
    )
    if local.returncode == 0:
        local_tip = (local.stdout or "").strip().lower()
        # tip 一致（追加の git 呼び出し不要・段2 で確認済みの `observed` を再利用）を
        # 先に見る——不一致ならこの時点で衝突確定であり、worktree list を呼ぶ意味が無い。
        reclaimable = local_tip == observed and not _branch_checked_out_elsewhere(
            request.branch_name, cwd=workdir, runner=runner
        )
        if not reclaimable:
            raise BranchSourceError("BRANCH_ADOPT_LOCAL_EXISTS", request.branch_name)
        deleted = _run_git(
            ["git", "branch", "-D", request.branch_name], cwd=workdir, runner=runner
        )
        if deleted.returncode != 0:
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
