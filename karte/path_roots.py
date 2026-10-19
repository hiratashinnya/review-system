"""Internal path handling for the karte package."""

from pathlib import Path

from .path_errors import KartePathError

def _resolved_root(repo_root) -> Path:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise KartePathError(f"repo-root がディレクトリでない: {root}")
    return root

def main_worktree_root(candidate) -> Path:
    """``candidate`` から main worktree の root を決定論的に導出する（K-01）。

    ``karte`` パッケージ自体が linked worktree（``git worktree add``）にチェックアウト
    されて実行されうる（``issue-implementer`` は isolated worktree で走る前提）。
    ``Path(__file__)`` 由来の候補パスをそのまま repo-root にすると、worktree ごとに
    ``tmp/_karte/`` が分裂し、レビューアの ``ingest-review`` と是正側の ``append`` が
    別々の台帳を見てしまう。

    判定は ``candidate/.git`` の種別で行う:
      * **ディレクトリ**なら通常のリポジトリ（main worktree そのもの）＝ ``candidate`` を返す。
      * **ファイル**なら linked worktree の目印。中身は ``gitdir: <path>`` で、共有 git
        ディレクトリ配下の worktree 別サブディレクトリを指す。``<gitdir>/commondir``
        （実在すれば）が共有 ``.git`` ディレクトリへの相対パスを持つので、それを解決して
        その親を main worktree root とする。``commondir`` が無い簡易環境では、標準レイアウト
        ``<main>/.git/worktrees/<name>`` の ``.git`` セグメントから同じ結果を導出する。
      * ``.git`` が無い（git 管理下でない裸ディレクトリ等）場合は ``candidate`` をそのまま返す
        （git 未使用のテスト環境まで拒否すると既存呼び出しを壊すため）。

    ここで返す値は「どこを repo-root として扱うか」の**候補**にすぎない。実際の読み書きは
    引き続き ``_resolved_root`` / ``resolve_within_repo`` のガード1〜5を必ず通る
    （ここでガードを迂回しない）。
    """
    root = Path(candidate).resolve()
    git_path = root / ".git"
    if git_path.is_dir():
        return root
    if not git_path.is_file():
        return root

    text = git_path.read_text(encoding="utf-8", errors="replace").strip()
    prefix = "gitdir:"
    if not text.startswith(prefix):
        raise KartePathError(
            f".git ファイルの形式が不正（'gitdir:' で始まらない）: {git_path}"
        )
    gitdir = Path(text[len(prefix):].strip())
    if not gitdir.is_absolute():
        gitdir = root / gitdir
    gitdir = gitdir.resolve()

    commondir_file = gitdir / "commondir"
    if commondir_file.is_file():
        common_rel = commondir_file.read_text(encoding="utf-8", errors="replace").strip()
        common_dir = (gitdir / common_rel).resolve()
        return common_dir.parent

    # `commondir` が無い簡易環境向けフォールバック：標準レイアウト
    # `<main>/.git/worktrees/<name>` の `.git` セグメントから導出する。
    parts = gitdir.parts
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == ".git":
            return Path(*parts[: index + 1]).parent
    raise KartePathError(
        f"gitdir から main worktree の root を導出できない（commondir も無い）: {gitdir}"
    )

def invoking_worktree_root(candidate) -> Path:
    """``candidate``（呼び出し元 worktree のルート候補）を検証してそのまま返す（Issue #437）。

    :func:`main_worktree_root` と対になる関数だが**変換はしない**。あちらは linked worktree
    （``issue-implementer``/``issue-fixer`` の isolated worktree）を main worktree へ収束させる
    ——台帳（``tmp/_karte/``）は worktree 間で共有すべき単一の正本だから。一方 ``git diff`` の
    対象は**呼び出し元 worktree そのものの変更**であり、同じ収束をかけると isolated worktree
    で行った commit が main worktree の作業ツリーには存在しないため diff が常に空になり、
    Issue #355 の空 diff fail-close が spurious に発火する（Issue #437 の症状そのもの）。
    ここでは ``candidate`` が実在するディレクトリかどうかの検証だけを行い、パスはそのまま返す。
    """
    return _resolved_root(candidate)
