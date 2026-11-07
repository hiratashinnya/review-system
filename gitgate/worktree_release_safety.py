"""Release reason formatting, lock diagnosis, and guarded worktree removal."""

from .worktree_models import WorktreeError
from .worktree_path_validation import resolve_within
from .worktree_git_runtime import _run_git
from .worktree_git_records import _is_git_managed

def _reason_note(verb: str, reason: str, *, flag: str = "") -> str:
    """受理した ``--reason`` を notes 用の1行に整形する（空 reason なら空文字）。

    **受理・検証まで通った ``--reason`` は必ず台帳に残す**（F-354-04）。``--force-uncollected`` /
    ``--allow-missing-handoff`` と一緒に渡されたときだけ記録する作りだと、単独で渡された理由が
    「記録された」と誤認されたまま失われる（PR8 区分1 が保全対象とする一次情報の取りこぼし）。
    """
    if not reason:
        return ""
    return f"{verb} {flag}: {reason}" if flag else f"{verb}: {reason}"

def _is_worktree_lock_failure(detail: str | None) -> bool:
    """``git worktree remove`` の失敗が **worktree ロック**由来か（Issue #464・F-464-01 是正）。

    停止途中のエージェントプロセスが worktree を掴んだままだと
    ``fatal: cannot remove a locked working tree, lock reason: ...`` で失敗する。
    git のロック時メッセージは版差があるが、いずれも "locked working tree" または
    "locked worktree" という**連結した語句**を含む。この判定は連結一致に絞る——
    「"lock" と "working tree"/"worktree" がそれぞれ独立に含まれるか」を見ていた旧実装は、
    削除対象パスが常に ``.claude/worktrees/agent-<id>`` を含むため後半の条件がほぼ常に真になり
    実効条件が ``"lock" in stderr`` だけに縮退していた（F-464-01）。結果として
    ``fatal: Unable to create '<repo>/.git/worktrees/agent-x/index.lock': File exists.`` の
    ような ``index.lock``（別レイヤのロック＝非 worktree ロック失敗）も誤って worktree ロック
    と判定し、本来 ``stale``（``ISSUE_START_WORKTREE_RESIDUE`` で解消コマンド付き deny）へ
    落ちるべきものが ``release_pending``（deny 網の外）へ落ちうる不具合があった。連結一致に
    絞ることで、``index.lock`` 等の別レイヤのロックは "locked working tree"/"locked worktree"
    を含まないため誤マッチしない。ロック以外の削除失敗（権限・submodule 等）は対象にしない
    ——それらは従来どおり ``WORKTREE_REMOVE_FAILED`` を送出して fail-close させる。
    """
    if not detail:
        return False
    lowered = detail.lower()
    return "locked working tree" in lowered or "locked worktree" in lowered

def _remove_worktree_dir(repo_root, relative: str, *, runner) -> bool:
    """``relative`` の実体を削除する。既に無ければ ``False``（冪等）。

    「何を消してよいか」の判定はここに集約する——``resolve_within``（構成要素の symlink 検査＋
    repo-root 外への脱出検査）と ``git worktree list --porcelain`` への登録確認の**両方**を
    通ったパスだけが ``git worktree remove`` に渡る。呼び出し側は「消してよい状態か」だけを
    判断し、「消してよいパスか」の判断は持たない。
    """
    target = resolve_within(repo_root, relative)
    if not target.exists():
        # 既に無い＝解放済みとみなす（`git worktree remove` の失敗を冪等化する）。
        _run_git(["git", "worktree", "prune"], cwd=repo_root, runner=runner)
        return False
    if not target.is_dir():
        raise WorktreeError("WORKTREE_PATH_NOT_DIR", str(target))
    if not _is_git_managed(target, repo_root, runner=runner):
        raise WorktreeError(
            "WORKTREE_NOT_GIT_MANAGED",
            f"{relative}（git の linked worktree として登録されていない）",
        )
    removed = _run_git(
        ["git", "worktree", "remove", "--force", str(target)], cwd=repo_root, runner=runner
    )
    if removed.returncode != 0:
        raise WorktreeError("WORKTREE_REMOVE_FAILED", (removed.stderr or "").strip()[:400])
    _run_git(["git", "worktree", "prune"], cwd=repo_root, runner=runner)
    return True
