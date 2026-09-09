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

失敗文言に「誰が掴んでいるか」を載せる（Issue #502）
--------------------------------------------------
``BRANCH_ADOPT_LOCAL_EXISTS`` は**復旧手順へ直結する**必要がある。旧実装はブランチ名しか
返さず、主文脈が ``tmp/_worktree/ledger.json`` と ``.git/worktrees/`` を手で突き合わせる
羽目になっていた（Issue #502 の実測）。:func:`describe_local_ref_conflict` が掴んでいる主体を
区別して文言に載せる:

* **primary checkout（メインワークツリー）** — `pr-reviewer` 等が差分確認のためブランチを
  切り替えたまま戻していない場合（Issue #502 観測2）。``gitgate`` の worktree verb では
  解消できないので、``git switch <既定ブランチ>`` へ誘導する。
* **agent worktree** — 異常終了で残った dispatch の worktree（同観測1）。台帳エントリ
  （``entry_id`` と ``status``）を引けたら併記し、``collect-worktree --entry`` へ誘導する。
* **その他の linked worktree** — 台帳の管理外。パスを出して手当てを促す。
* **tip 不一致** — そもそも掴んでいる主体の問題ではなく、正体不明のローカル作業がある。
  ``git worktree list`` を呼ばずに local/origin の OID を出して止める（既存の
  短絡判定を維持する＝呼ぶ意味が無い）。

台帳の参照は**best-effort**（診断のためだけ）で、引けなくても判定（fail-close）は変わらない。

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

import os
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

# stage 1 の `git fetch` 用タイムアウト（秒）。到達不能/認証待ちで無期限にハングしないよう、
# CI/自動化文脈での妥当な既定値として 30 秒を採る（Issue #426・F-426-05。worktree.py 側の
# `_cleanup_branch_ref` と同じ既定値・同じ根拠）。
FETCH_TIMEOUT_SECONDS = 30

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
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """``timeout``/``env`` は明示的に渡されたときだけ ``runner`` へ転送する。

    ネットワーク I/O が起こりうる呼び出し（stage 1 の ``git fetch``）だけがこの2つを渡し、
    それ以外の純ローカル操作（``rev-parse``/``switch``/``branch`` 等）は従来どおり渡さない
    （Issue #426・F-426-05——ハングしうるのは fetch だけなので、対象を広げない）。
    """
    kwargs: dict = {}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if env is not None:
        kwargs["env"] = env
    return runner(
        list(argv), cwd=str(cwd), text=True, capture_output=True, shell=False, **kwargs
    )


def _fetch_env() -> dict:
    """``git fetch`` を非対話化する env（stdin 経由の認証プロンプト待ちでハングしないため）。

    ``worktree.py::_fetch_env`` と同じ考え方——``os.environ`` を丸ごと引き継いだ上で
    ``GIT_TERMINAL_PROMPT=0`` だけを上書きする（他の env を握り潰さない）。
    """
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


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


HOLDER_PRIMARY = "primary"
HOLDER_AGENT = "agent-worktree"
HOLDER_LINKED = "linked-worktree"
HOLDER_UNKNOWN = "unknown"

# `.claude/worktrees/agent-<id>` の形（`issue_start.worktree_ledger.WORKTREE_PATH_RE` と同じ
# 形状だが、ここでは絶対パスの末尾に対する部分一致で使うので独立に持つ）。
_AGENT_WORKTREE_SUFFIX = re.compile(r"\.claude/worktrees/agent-[A-Za-z0-9_-]{1,64}$")


def _branch_holder(
    branch_name: str, *, cwd: Path, runner: Callable[..., subprocess.CompletedProcess]
) -> tuple[str | None, str | None]:
    """``branch_name`` を checked out している worktree を種別つきで返す（Issue #502）。

    返り値は ``(種別, パス)``。種別は :data:`HOLDER_PRIMARY`（porcelain の先頭レコード＝
    メインワークツリー）／:data:`HOLDER_AGENT`（``.claude/worktrees/agent-<id>``）／
    :data:`HOLDER_LINKED`（その他の linked worktree）／:data:`HOLDER_UNKNOWN`
    （``git worktree list`` が失敗＝判定不能）／``None``（どこも掴んでいない）。

    到達不能・異常終了は「わからない」を「安全（checked out されていない）」に潰さず、
    :data:`HOLDER_UNKNOWN` にする——fail-close。stray ref の自動回収は「明確に無害と確認
    できたときだけ」行う契約なので、判定不能を無害側に倒さない。
    """
    completed = _run_git(
        ["git", "worktree", "list", "--porcelain"], cwd=cwd, runner=runner
    )
    if completed.returncode != 0:
        return HOLDER_UNKNOWN, None
    target = f"branch refs/heads/{branch_name}"
    index = -1
    path: str | None = None
    for line in (completed.stdout or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("worktree "):
            index += 1
            path = stripped[len("worktree "):].strip()
            continue
        if stripped != target:
            continue
        if index == 0:
            return HOLDER_PRIMARY, path
        if path and _AGENT_WORKTREE_SUFFIX.search(path.replace("\\", "/")):
            return HOLDER_AGENT, path
        return HOLDER_LINKED, path
    return None, None


def _ledger_entry_for_worktree(holder_path: str | None, *, cwd: Path):
    """掴んでいる worktree に対応する台帳エントリ（best-effort・引けなければ ``None``）。

    診断文言を厚くするためだけの参照であり、**判定（fail-close）には一切使わない**。
    台帳が読めない・パスが main worktree の外・そもそも台帳が無い、のいずれでも黙って
    ``None`` を返す（ここで例外を外へ出すと、診断のために adopt が別の理由で落ちる）。
    """
    if not holder_path:
        return None
    try:
        from issue_start.worktree_ledger import main_worktree_root

        from .worktree import find_entry

        root = Path(main_worktree_root(cwd))
        relative = Path(holder_path).resolve().relative_to(root.resolve()).as_posix()
        return find_entry(root, worktree_path=relative)
    except Exception:  # noqa: BLE001 - 診断が引けないことで adopt を落とさない
        return None


def describe_local_ref_conflict(
    branch_name: str,
    *,
    holder_kind: str | None,
    holder_path: str | None = None,
    entry=None,
    local_tip: str | None = None,
    remote_tip: str | None = None,
) -> str:
    """``BRANCH_ADOPT_LOCAL_EXISTS`` の detail を組み立てる（純関数・Issue #502）。

    「何が起きたか」だけでなく「**誰が掴んでいるか**」と「次に何を実行するか」を必ず含める。
    """
    if holder_kind == HOLDER_PRIMARY:
        return (
            f"{branch_name}（**メインワークツリー（primary checkout）** "
            f"{holder_path or '<path unknown>'} が同じブランチを checkout したままになっている。"
            "agent worktree ではないので gitgate の worktree verb では解消しない。"
            "解消: そのワークツリーで `git switch <既定ブランチ>` を実行して戻す"
            "（レビュー担当がブランチを切り替えたまま戻していない場合がある＝Issue #502 観測2））"
        )
    if holder_kind in (HOLDER_AGENT, HOLDER_LINKED):
        if entry is not None:
            attribution = (
                f"台帳 entry={entry.get('entry_id')}[{entry.get('status')}]"
            )
            remedy = (
                "解消: python3 -m gitgate collect-worktree --entry "
                f"{entry.get('entry_id')}"
                "（回収不能なら python3 -m gitgate worktree-forget --entry "
                f"{entry.get('entry_id')} --reason <text> のあと "
                "python3 -m gitgate worktree-release <path> --force-uncollected --reason <text>）"
            )
        else:
            attribution = "台帳に対応するエントリが無い"
            remedy = (
                "解消: python3 -m gitgate worktree-release <path> --force-uncollected "
                "--reason <text>（主文脈が実行する）"
            )
        label = "agent worktree" if holder_kind == HOLDER_AGENT else "linked worktree"
        return (
            f"{branch_name}（{label} {holder_path or '<path unknown>'} が同じブランチを"
            f"掴んでいる。{attribution}。{remedy}）"
        )
    if holder_kind == HOLDER_UNKNOWN:
        return (
            f"{branch_name}（ローカル ref が残っているが `git worktree list` を実行できず、"
            "どのワークツリーが掴んでいるか判定できない。判定不能は衝突側に倒す＝fail-close）"
        )
    return (
        f"{branch_name}（ローカル ref が origin と別のコミットを指す: "
        f"local={local_tip or '<unknown>'} / origin={remote_tip or '<unknown>'}。"
        "未 push のローカル作業がありうるため自動回収しない。内容を確認したうえで手当てする）"
    )


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
    # timeout/env は Issue #426・F-426-05 の是正——到達不能/認証待ちの origin で無期限に
    # ハングせず、他の fetch 失敗と同じ fail-close（BRANCH_GIT_ERROR）で有限時間に落ちる。
    try:
        fetch_completed = _run_git(
            ["git", "fetch", "--prune", "origin"],
            cwd=workdir,
            runner=runner,
            timeout=FETCH_TIMEOUT_SECONDS,
            env=_fetch_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise BranchSourceError(
            "BRANCH_GIT_ERROR", f"fetch timed out after {FETCH_TIMEOUT_SECONDS}s"
        ) from exc
    _require_ok(fetch_completed, "BRANCH_GIT_ERROR", "fetch")

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
        if local_tip != observed:
            raise BranchSourceError(
                "BRANCH_ADOPT_LOCAL_EXISTS",
                describe_local_ref_conflict(
                    request.branch_name,
                    holder_kind=None,
                    local_tip=local_tip,
                    remote_tip=observed,
                ),
            )
        holder_kind, holder_path = _branch_holder(
            request.branch_name, cwd=workdir, runner=runner
        )
        if holder_kind is not None:
            # 掴んでいる主体を失敗文言に載せて復旧手順へ直結させる（Issue #502）。
            # 台帳参照は best-effort で、引けなくても fail-close の判定は変わらない。
            entry = (
                _ledger_entry_for_worktree(holder_path, cwd=workdir)
                if holder_kind in (HOLDER_AGENT, HOLDER_LINKED)
                else None
            )
            raise BranchSourceError(
                "BRANCH_ADOPT_LOCAL_EXISTS",
                describe_local_ref_conflict(
                    request.branch_name,
                    holder_kind=holder_kind,
                    holder_path=holder_path,
                    entry=entry,
                ),
            )
        deleted = _run_git(
            ["git", "branch", "-D", request.branch_name], cwd=workdir, runner=runner
        )
        if deleted.returncode != 0:
            raise BranchSourceError(
                "BRANCH_ADOPT_LOCAL_EXISTS",
                f"{request.branch_name}（無害な残留 ref と判定したが `git branch -D` に"
                f"失敗した: {(deleted.stderr or '').strip()[:200]}）",
            )

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
