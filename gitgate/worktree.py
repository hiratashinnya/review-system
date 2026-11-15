"""Worktree release, collection, forget and sweep operations.

Safety and lifecycle rationale: .ai/rationale/gitgate-worktree-safety.md.
Public function imports and the established CLI contract remain available here.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from issue_start.worktree_ledger import (
    DEFERRED_RELEASE_STATUS,
    ENTRY_ID_RE,
    WORKTREE_PATH_RE,
    LedgerError,
    add_note,
    main_worktree_root,
    mark,
    read_ledger,
)

# `git fetch` 用のタイムアウト（秒）。到達不能/認証待ちで無期限にハングしないよう、CI/自動化
# 文脈での妥当な既定値として 30 秒を採る（Issue #426・F-426-05）。

from .worktree_models import (
    WorktreeError, ReleaseRequest, CollectRequest, ForgetRequest, SweepRequest,
    SweepEntryOutcome, ReleaseOutcome, CollectOutcome,
)
from .worktree_arg_common import _reject_control_chars, _validate_entry_id, _validate_reason, _parse_flags, _MAX_REASON_LEN
from .worktree_arg_release import parse_worktree_release_args, parse_collect_worktree_args
from .worktree_arg_lifecycle import parse_worktree_forget_args, parse_worktree_sweep_args
from .worktree_path_validation import validate_worktree_path, resolve_within
from .worktree_handoff_paths import (
    HANDOFF_DIR_PARTS, HANDOFF_FILENAME_RE, _SAFE_PATH_PART_RE,
    validate_handoff_relpath, validate_collect_dest,
)
from .worktree_git_runtime import _run_git, _fetch_env
from .worktree_git_records import worktree_records, linked_worktree_paths, _is_git_managed


from .worktree_config import FETCH_TIMEOUT_SECONDS, DEFAULT_MAX_HANDOFF_BYTES, COLLECTED_DIRNAME
from .worktree_ledger_access import _entries, find_entry, _mark, _note
from .worktree_release_safety import _reason_note, _is_worktree_lock_failure, _remove_worktree_dir
from .worktree_branch_cleanup import _cleanup_branch_ref
from .worktree_release_flow import worktree_release
from .worktree_handoff_io import _read_handoff, _write_collected, _ensure_collected_dir
from .worktree_collect_flow import collect_worktree_flow as _collect_worktree_flow

def collect_worktree(
    repo_root,
    *,
    entry_id: str | None = None,
    worktree_path: str | None = None,
    handoff_path: str | None = None,
    into: str | None = None,
    allow_missing_handoff: bool = False,
    reason: str = "",
    now,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    max_bytes: int = DEFAULT_MAX_HANDOFF_BYTES,
    release: bool = True,
) -> CollectOutcome:
    """Collect a handoff and release its worktree; retain facade injection seams."""
    return _collect_worktree_flow(
        repo_root, entry_id=entry_id, worktree_path=worktree_path,
        handoff_path=handoff_path, into=into,
        allow_missing_handoff=allow_missing_handoff, reason=reason,
        now=now, runner=runner, max_bytes=max_bytes, release=release,
        read_handoff=_read_handoff, write_collected=_write_collected,
        release_fn=worktree_release,
    )

# --- verb: worktree-forget -----------------------------------------------------


def worktree_forget(repo_root, entry_id: str, *, reason: str, now) -> dict:
    """回収不能な ``stale`` エントリを ``abandoned`` へ逃がす（**worktree は消さない**）。

    PR-3 の deny が恒久的にパイプラインを止めるのを防ぐ唯一の逃げ道なので、``reason`` を
    必須にして「なぜ諦めたか」を必ず残す。**エントリは削除しない**（PR8 区分1＝保全対象）。

    ディスク上に実体が残っている場合は、この verb の**後で** :func:`worktree_release` を
    呼んで削除する（``abandoned`` のまま実体だけ消える）。この2手順以外に実体を消す経路は
    無い——回収の記録（``abandoned`` の理由）と実体の削除を1つの verb に混ぜない。
    """
    _validate_entry_id(entry_id)
    _validate_reason(reason)
    entry = find_entry(repo_root, entry_id=entry_id)
    if entry is None:
        raise WorktreeError("WORKTREE_ENTRY_NOT_FOUND", entry_id)
    if entry.get("status") == "abandoned":
        # 冪等: 既に abandoned なら理由を1行足すだけ（状態機械は進めない）。
        try:
            add_note(repo_root, entry_id, now=now, note=f"worktree-forget (repeat): {reason}")
        except LedgerError as exc:
            raise WorktreeError(exc.reason, exc.detail) from exc
        return find_entry(repo_root, entry_id=entry_id)
    _mark(repo_root, entry_id, "abandoned", now=now, note=f"worktree-forget: {reason}")
    return find_entry(repo_root, entry_id=entry_id)


# --- verb: worktree-sweep-abandoned ---------------------------------------------

# 掃引で台帳へ残す marker（notes を grep すれば「なぜ解放されたか」が後から辿れる）。
SWEEP_MARKER = "worktree-sweep-abandoned"


def _own_handoff(repo_root, entry) -> tuple:
    """エントリの worktree から**その dispatch 自身の** handoff を1つに決める。

    返り値は ``(相対パス | None, how)``。``how`` は ``unique`` / ``empty`` / ``ambiguous`` /
    ``unreadable`` / ``unidentifiable``。判定規則は
    ``issue_start/subagent_hooks.py::_discover_handoff`` と同一（``<agent_type>--issue-<N>``
    に一致するものだけを自分の成果物とみなす）で、委譲先エージェントの handoff を自分のものと
    取り違えない（Issue #423 の実測）。**規則は同一だが実装は共有しない**——フック側は
    「``gitgate`` を import せず起動するだけ」という境界を保つために独自に組み立てており、
    こちらは ``gitgate`` 側の正本である :data:`HANDOFF_FILENAME_RE` をそのまま使う。
    """
    agent_type = entry.get("agent_type")
    issue = entry.get("issue")
    relative = entry.get("worktree_path")
    if not isinstance(agent_type, str) or not agent_type:
        return None, "unidentifiable"
    if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
        return None, "unidentifiable"
    try:
        worktree_dir = resolve_within(repo_root, relative)
    except WorktreeError:
        return None, "unreadable"
    directory = worktree_dir / HANDOFF_DIR_PARTS[0] / HANDOFF_DIR_PARTS[1]
    if directory.is_symlink():
        return None, "unreadable"
    if not directory.exists():
        return None, "empty"
    if not directory.is_dir():
        return None, "unreadable"
    try:
        names = sorted(child.name for child in directory.iterdir() if not child.is_dir())
    except OSError:
        return None, "unreadable"
    mine = []
    for name in names:
        match = HANDOFF_FILENAME_RE.fullmatch(name)
        if match is None:
            continue
        if match.group("agent") != agent_type or int(match.group("issue")) != issue:
            continue
        mine.append(name)
    if not mine:
        return None, "empty"
    if len(mine) > 1:
        return None, "ambiguous"
    return f"{'/'.join(HANDOFF_DIR_PARTS)}/{mine[0]}", "unique"


def _is_worktree_clean(repo_root, entry, *, runner) -> tuple:
    """作業ツリーに未コミット/未追跡の変更が無いことを確認する（Issue #502・F-502-01）。

    返り値は ``(bool, 理由)``。真を返すのは ``git status --porcelain`` を実際に実行できて、
    その出力が空だったときだけ——**判定できなかったときは偽**（fail-close）。
    「見られなかった」を「捨ててよい」に潰さない。

    **この関門は handoff の有無で免除しない**。実体を消す :func:`_remove_worktree_dir` は
    ``git worktree remove --force`` を使い、dirty / untracked を問答無用で消す。handoff を
    書き終えていることは「作業ツリーに未コミットの何かが残っていない」ことを含意しないため、
    handoff がある経路（:func:`_sweep_one` の ``how == "unique"``）でも回収の**後で**必ず通す。
    """
    relative = entry.get("worktree_path")
    try:
        target = resolve_within(repo_root, relative)
    except WorktreeError as exc:
        return False, f"worktree のパスを解決できない（{exc.reason}）"
    if not target.is_dir():
        return False, "worktree の実体が無い"
    status = _run_git(["git", "status", "--porcelain"], cwd=target, runner=runner)
    if status.returncode != 0:
        return False, "git status を実行できない（判定不能）"
    if (status.stdout or "").strip():
        return False, "作業ツリーに未コミット/未追跡の変更がある"
    return True, ""


def _is_discardable(repo_root, entry, *, runner) -> tuple:
    """handoff が無い worktree を「捨ててよい」と**積極的に確認**する（Issue #502）。

    返り値は ``(bool, 理由)``。真を返すのは次の**すべて**を観測できたときだけで、1つでも
    観測できなければ偽（fail-close）——「判定できなかった」を「捨ててよい」に潰さない。

    1. 台帳に ``branch_name`` がある（origin 包含を判定する相手が決まる）。
    2. 作業ツリーが clean（:func:`_is_worktree_clean`）＝未コミットの変更も未追跡
       ファイルも無い。
    3. ``HEAD`` が fresh fetch 後の ``refs/remotes/origin/<branch_name>`` に含まれる
       ＝未 push のコミットが無い。

    これは Issue #502 で主文脈が手作業で確認した内容（「作業ツリー clean・HEAD が remote と
    同一・ハンドオフ未作成で、失われる作業は無かった」）を機械化したものである。
    条件2 は handoff がある経路でも必要なので :func:`_is_worktree_clean` へ切り出してある
    （F-502-01）。
    """
    relative = entry.get("worktree_path")
    branch_name = entry.get("branch_name")
    if not isinstance(branch_name, str) or not branch_name:
        return False, "台帳に branch_name が無く origin 包含を判定できない"
    clean, why = _is_worktree_clean(repo_root, entry, runner=runner)
    if not clean:
        return False, why
    try:
        target = resolve_within(repo_root, relative)
    except WorktreeError as exc:  # pragma: no cover - 直前の clean 検査が同じ解決に成功済み
        return False, f"worktree のパスを解決できない（{exc.reason}）"
    try:
        fetched = _run_git(
            ["git", "fetch", "--prune", "origin"],
            cwd=target,
            runner=runner,
            timeout=FETCH_TIMEOUT_SECONDS,
            env=_fetch_env(),
        )
    except Exception as exc:  # noqa: BLE001 - 判定不能は「捨ててよい」に倒さない
        return False, f"origin の fetch に失敗した（{type(exc).__name__}）"
    if fetched.returncode != 0:
        return False, "origin の fetch に失敗した（判定不能）"
    ancestor = _run_git(
        [
            "git", "merge-base", "--is-ancestor",
            "HEAD", f"refs/remotes/origin/{branch_name}",
        ],
        cwd=target,
        runner=runner,
    )
    if ancestor.returncode != 0:
        return False, f"HEAD が origin/{branch_name} に含まれない（未 push のコミットがありうる）"
    return True, ""


def _locked_worktree_paths(repo_root, *, runner) -> set:
    """``locked`` と報告された worktree の解決済み絶対パス集合。"""
    locked = set()
    for record in worktree_records(repo_root, runner=runner):
        if not record.get("locked"):
            continue
        try:
            locked.add(str(Path(record["path"]).resolve()))
        except OSError:
            continue
    return locked


def sweep_abandoned_running(
    repo_root,
    *,
    now,
    reason: str,
    no_live_dispatch: bool = False,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list:
    """異常終了で ``running`` のまま残ったエントリを回収・解放する（Issue #502・観測1）。

    ``no_live_dispatch`` が偽なら**台帳も git も一切触らずに空を返す**。``running`` は
    「入れ子委譲待ちの正当な保留」でもあり（Issue #423）、状態だけでは異常終了と区別
    できないため、区別は呼び出し地点の観測（live な dispatch が1つも無い＝レートリミット
    復帰イベントで**当該ペインが**アイドル）に委ねる。その観測をこの引数として**明示的に**
    受け取ることで、「うっかり普通の dispatch 経路から呼ぶ」ことが構造的に無害化される。
    ただしこの観測が届くのは呼び出し元が見ている1ペインだけで、別ペインの live な dispatch を
    守るのは ``locked`` 判定である（モジュール docstring の ``worktree-sweep-abandoned`` 節）。

    掃引は entry ごとに独立で、1件の失敗が他を巻き込まない（例外を外へ出さない）。
    ``action`` の値:

    ==================  ==========================================================
    ``released``        回収（または捨ててよい確認）を経て worktree を解放した
    ``release-pending`` 回収は済んだが削除だけ git ロックで遅延した（Issue #464）
    ``kept-locked``     ``git worktree list`` が ``locked`` と報告した＝live とみなし触らない
    ``kept-unsafe``     捨ててよいと確認できなかった＝解放せず ``stale`` へ落とした
                        （handoff が無い場合は回収前の ``_is_discardable``、handoff がある
                        場合は**回収後**の clean 検査で落ちたもの＝F-502-01）
    ``kept-unresolved`` handoff を一意に決められない＝解放せず ``stale`` へ落とした
    ``kept-error``      回収・解放が失敗した＝``stale`` へ落とした
    ==================  ==========================================================

    ``stale`` へ落としたものは既存の ``ISSUE_START_WORKTREE_RESIDUE``（解消コマンド付き
    deny）が次 dispatch で拾う——**黙って残さない**。
    """
    if not no_live_dispatch:
        return []
    _validate_reason(reason)
    candidates = [
        entry
        for entry in _entries(repo_root)
        if entry.get("status") == "running"
        and isinstance(entry.get("entry_id"), str)
        and isinstance(entry.get("worktree_path"), str)
        and entry.get("worktree_path")
    ]
    if not candidates:
        return []
    try:
        locked = _locked_worktree_paths(repo_root, runner=runner)
    except Exception:  # noqa: BLE001 - 判定材料が読めないなら何もしない（fail-safe）
        return []

    outcomes: list = []
    for entry in candidates:
        entry_id = entry["entry_id"]
        relative = entry["worktree_path"]
        try:
            outcomes.append(
                _sweep_one(
                    repo_root,
                    entry,
                    now=now,
                    reason=reason,
                    locked=locked,
                    runner=runner,
                )
            )
        except Exception as exc:  # noqa: BLE001 - 1件の事故で掃引全体を止めない
            outcomes.append(
                SweepEntryOutcome(
                    entry_id, relative, "kept-error", type(exc).__name__
                )
            )
    return outcomes


def _sweep_stale(repo_root, entry_id, *, now, note) -> None:
    try:
        _mark(repo_root, entry_id, "stale", now=now, note=note)
    except WorktreeError:
        # 記録できなくても掃引は続ける（残留は gate の deny が別途拾う）。
        pass


def _sweep_one(repo_root, entry, *, now, reason, locked, runner) -> SweepEntryOutcome:
    entry_id = entry["entry_id"]
    relative = entry["worktree_path"]
    try:
        resolved = str((Path(repo_root).resolve() / relative).resolve())
    except OSError:
        resolved = ""
    if resolved and resolved in locked:
        # ハーネスがロックしている＝live な dispatch が掴んでいる。触らない（#423 の保護）。
        return SweepEntryOutcome(
            entry_id, relative, "kept-locked", "git が locked と報告した worktree"
        )

    handoff, how = _own_handoff(repo_root, entry)
    if how in ("ambiguous", "unreadable", "unidentifiable"):
        _sweep_stale(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"{SWEEP_MARKER}: 自分の handoff を一意に決められない（{how}）ため解放しない。"
                f"主文脈が collect-worktree / worktree-forget で処置する（Issue #502）: {reason}"
            ),
        )
        return SweepEntryOutcome(entry_id, relative, "kept-unresolved", how)

    if how == "empty":
        discardable, why = _is_discardable(repo_root, entry, runner=runner)
        if not discardable:
            _sweep_stale(
                repo_root,
                entry_id,
                now=now,
                note=(
                    f"{SWEEP_MARKER}: handoff が無く、捨ててよいと確認できなかったため解放しない"
                    f"（{why}）。主文脈が内容を確認して処置する（Issue #502）: {reason}"
                ),
            )
            return SweepEntryOutcome(entry_id, relative, "kept-unsafe", why)

    _mark(
        repo_root,
        entry_id,
        "stopped",
        now=now,
        note=(
            f"{SWEEP_MARKER}: live な dispatch が1つも無い地点（レートリミット復帰）で "
            f"running が残っていたため、異常終了として停止を確定した（Issue #502・handoff={how}）"
            f": {reason}"
        ),
    )
    # 回収（段1〜5）と解放（段6）を分けて呼ぶ。**回収を先に確定させる**ことで、この後の
    # clean 検査で解放を止めても成果物は `collected_to` へ退避済みになる（F-502-01）。
    try:
        collected = collect_worktree(
            repo_root,
            entry_id=entry_id,
            handoff_path=handoff,
            allow_missing_handoff=handoff is None,
            reason=f"{SWEEP_MARKER}: {reason}",
            now=now,
            runner=runner,
            release=False,
        )
    except WorktreeError as exc:
        _sweep_stale(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"{SWEEP_MARKER}: 回収に失敗した（{exc.reason}）。"
                f"主文脈が処置する（Issue #502）: {reason}"
            ),
        )
        return SweepEntryOutcome(entry_id, relative, "kept-error", exc.reason)

    if how == "unique":
        # handoff がある経路にも clean 検査を通す（F-502-01）。`git worktree remove --force`
        # は dirty/untracked を問答無用で消すため、「handoff が書けている＝完走した」を
        # 「捨ててよい」の代わりにしない。`how == "empty"` は上の `_is_discardable` で
        # 同じ検査（＋origin 包含）を既に通しているので二重には実行しない。
        clean, why = _is_worktree_clean(repo_root, entry, runner=runner)
        if not clean:
            _sweep_stale(
                repo_root,
                entry_id,
                now=now,
                note=(
                    f"{SWEEP_MARKER}: handoff は回収した"
                    f"（collected_to={collected.collected_to or '-'}）が、作業ツリーが clean と"
                    f"確認できなかったため解放しない（{why}）。主文脈が内容を確認して処置する"
                    f"（Issue #502）: {reason}"
                ),
            )
            return SweepEntryOutcome(entry_id, relative, "kept-unsafe", why)

    # 段6 だけをやり直す（エントリは `collected`）。`release_pending` への遅延（Issue #464）を
    # 含む解放段の契約をそのまま再利用するため、`worktree_release` を直接呼ばない。
    # `reason` は回収段で既に台帳へ書いているので渡さない（同じ理由を2回 notes に載せない）。
    try:
        outcome = collect_worktree(
            repo_root,
            entry_id=entry_id,
            now=now,
            runner=runner,
        )
    except WorktreeError as exc:
        _sweep_stale(
            repo_root,
            entry_id,
            now=now,
            note=(
                f"{SWEEP_MARKER}: 解放に失敗した（{exc.reason}）。"
                f"主文脈が処置する（Issue #502）: {reason}"
            ),
        )
        return SweepEntryOutcome(entry_id, relative, "kept-error", exc.reason)
    return SweepEntryOutcome(
        entry_id,
        relative,
        "released" if outcome.released else "release-pending",
        outcome.collected_to or "",
    )


def default_repo_root(candidate=None) -> Path:
    """CLI 既定の repo-root（linked worktree から起動されても main worktree へ収束させる）。"""
    try:
        return main_worktree_root(Path.cwd() if candidate is None else candidate)
    except LedgerError as exc:
        raise WorktreeError(exc.reason, exc.detail) from exc
