"""``cli.py`` の private helper に依存しない、別モジュールの verb 用の共通部品。"""

import functools
import sys
from pathlib import Path

from . import model, paths
from .active_pointer import read_active
from .errors import KarteNotFound, KarteUsageError
from .exit_codes import EXIT_ERROR, EXIT_NOT_FOUND

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def fail_close(func):
    """``cmd_*`` を「例外を投げず終了コードを返す」境界にする（``cli._fail_close`` と同じ契約）。"""

    @functools.wraps(func)
    def wrapper(args) -> int:
        try:
            return func(args)
        except KarteNotFound as exc:
            print(f"未検出: {exc}", file=sys.stderr)
            return EXIT_NOT_FOUND
        except (KarteUsageError, paths.KartePathError, model.KarteFormatError, OSError) as exc:
            print(f"拒否（fail-close）: {exc}", file=sys.stderr)
            return EXIT_ERROR

    return wrapper


def repo_root_of(args) -> Path:
    """台帳の repo-root。``args.repo_root``（テスト専用の上書き）が無ければ main worktree へ収束させる。"""
    override = getattr(args, "repo_root", None)
    return Path(override).resolve() if override else paths.main_worktree_root(_PACKAGE_ROOT)


def resolve_issue(args, repo_root) -> int:
    """``--issue`` が無ければ進行ポインタの ``issue``。ポインタが無い・壊れている・欠けるなら拒否する。"""
    if getattr(args, "issue", None) is not None:
        return paths.validate_issue(args.issue)
    active = read_active(repo_root, required=True)
    if "issue" not in active:
        raise KarteUsageError("--issue が未指定で、進行ポインタ tmp/_karte/active.json にも 'issue' が無い")
    return paths.validate_issue(active["issue"])


def next_round(repo_root, issue: int) -> int:
    """取り込み済みの最新ラウンド（進行ポインタの ``round``）＋1。欠落・非数値・Issue 不一致は拒否する。"""
    active = read_active(repo_root, required=True)
    if "round" not in active:
        raise KarteUsageError("進行ポインタに 'round' が無い（`activate --issue N` で作り直す）")
    text = str(active["round"])
    if not text.isdigit():
        raise KarteUsageError(f"進行ポインタの 'round' が 0 以上の整数でない: {active['round']!r}")
    if "issue" not in active or paths.validate_issue(active["issue"]) != issue:
        raise KarteUsageError(f"進行ポインタが指す issue-{active.get('issue')} と対象 issue-{issue} が食い違う")
    return int(text) + 1


def load_karte(repo_root, issue: int):
    """``(path, Karte)``。置き場・台帳が無ければ :class:`KarteNotFound`。"""
    try:
        path = paths.karte_path(issue, repo_root)
    except paths.KarteMissing as exc:
        raise KarteNotFound(f"{exc}（先に `activate --issue {issue}` と `ingest-reviewer` を実行する）") from None
    if not path.is_file():
        raise KarteNotFound(f"カルテが無い: {path}")
    return path, model.parse(paths.read_text(path))
