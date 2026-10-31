"""pr-reviewer が書ける唯一のファイル（``tmp/_handoff/pr-reviewer--*.md``）の判定規則。

Write フックと ``ingest-reviewer --from`` が同じ規則を使う（規則の分岐を作らない）。
"""

import re

from .path_errors import KartePathError
from .path_guard import resolve_within_repo

HANDOFF_DIRNAME = "_handoff"
REVIEWER_HANDOFF_RE = re.compile(r"^pr-reviewer--[A-Za-z0-9][A-Za-z0-9._-]*\.md$")


def resolve_reviewer_handoff(path, repo_root):
    """``path`` が ``<repo-root>/tmp/_handoff/pr-reviewer--*.md`` ならその正規化パスを返す。

    ``..``・symlink 構成要素・repo-root 外・別ディレクトリ・ファイル名の不一致は
    :class:`KartePathError`（fail-close）。
    """
    checked = resolve_within_repo(path, repo_root)
    root = resolve_within_repo(".", repo_root)
    if checked.parent != root / "tmp" / HANDOFF_DIRNAME:
        raise KartePathError(f"tmp/{HANDOFF_DIRNAME}/ の直下ではない: {checked}")
    if not REVIEWER_HANDOFF_RE.match(checked.name):
        raise KartePathError(
            f"ファイル名が pr-reviewer--<key>.md の形ではない: {checked.name}"
        )
    return checked
