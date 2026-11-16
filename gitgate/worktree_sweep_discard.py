"""Require clean worktree and remote ancestry before discarding no-handoff work."""

from .worktree_models import WorktreeError
from .worktree_path_validation import resolve_within
from .worktree_git_runtime import _run_git, _fetch_env
from .worktree_config import FETCH_TIMEOUT_SECONDS
from .worktree_sweep_clean import _is_worktree_clean

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
