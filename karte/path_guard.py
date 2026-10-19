"""Internal path handling for the karte package."""

import os
from pathlib import Path

from .path_errors import KartePathError
from .path_roots import _resolved_root

def resolve_within_repo(path, repo_root) -> Path:
    """``path`` が repo-root 配下の安全なパスかを検査し、正規化済みパスを返す。

    実在チェックは行わない（存在しないパスの「書き先」検査にも使うため）。
    ガード 1〜4 のいずれかに掛かれば :class:`KartePathError`（fail-close）。
    """
    root = _resolved_root(repo_root)
    given = Path(path)

    # ガード1: `..` は正規化より先に拒否する（正規化は symlink を無視して畳んでしまう）。
    if ".." in given.parts:
        raise KartePathError(
            f"'..' を含むパスは受け付けない（traversal 拒否）: {given}"
        )
    if not given.is_absolute():
        given = root / given

    # `.` と重複スラッシュのみを畳む（`..` は上で排除済みなので symlink を飛ばさない）。
    lexical = Path(os.path.normpath(str(given)))

    # ガード2: repo-root 配下か。
    try:
        rel = lexical.relative_to(root)
    except ValueError:
        raise KartePathError(
            f"repo-root の外を指している: {lexical}（repo-root={root}）"
        ) from None

    # ガード3: repo-root から対象までの各構成要素が symlink でないか。
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise KartePathError(
                f"パス構成要素が symlink: {cursor}（symlink 経由の読み書きは拒否）"
            )

    # ガード4: 実体解決後もなお repo-root 配下か（存在する範囲での再確認）。
    resolved = lexical.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise KartePathError(
            f"実体解決の結果 repo-root の外を指した: {lexical} → {resolved}"
        ) from None
    return lexical
