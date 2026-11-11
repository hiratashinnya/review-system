"""台帳の repo-root と ``git diff`` の cwd の解決（呼び出しごとの遅延解決）。

設計理由（repo-root の遅延解決・diff 用 cwd を main へ収束させない理由）は
[.ai/rationale/karte-module-split.md](../.ai/rationale/karte-module-split.md)。
"""

from pathlib import Path

from . import paths

# `karte` パッケージが置かれているディレクトリ（＝呼び出し元 worktree root の候補）。
# 台帳解決（`repo_root_of`）は main worktree へ変換するが、diff 計算（`invoking_worktree`）は
# 変換前のこの値をそのまま使う——両者を同じ変換に流用しない（Issue #437）。
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent

# repo-root のオーバーライド点（テスト専用）。**既定は None（＝未解決）**で、導出は
# `repo_root_of` が呼ばれたときに行う（K-12 の遅延評価）。全 verb がこの 1 箇所を通る。
_REPO_ROOT = None


def repo_root_of(args) -> Path:
    """台帳の repo-root を呼び出しごとに遅延解決する。順は ``args.repo_root``（テスト専用）、``_REPO_ROOT``、main worktree。"""
    override = getattr(args, "repo_root", None)
    if override:
        return Path(override).resolve()
    if _REPO_ROOT is not None:
        return Path(_REPO_ROOT)
    return paths.main_worktree_root(_PACKAGE_ROOT)


def invoking_worktree() -> Path:
    """``karte`` が今動いている worktree のルート（``git diff`` の cwd 用。main へは収束させない）。"""
    return paths.invoking_worktree_root(_PACKAGE_ROOT)
