"""申告 scope の原本ファイル（``tmp/_karte/issue-<N>.declared-scope.jsonl``）の読み書き部品。

1 行 1 レコード：レビューアの申告またはオーナーの確定。書込みは常に既存の全行を検証し、
新しい全体を同じディレクトリの一時ファイルへ書いて置換する。
"""

from pathlib import Path

from . import paths
from .scope_atomic import write_scope_text
from .scope_directory import open_scope_directory
from .scope_ledger_io import read_scope_text, scope_entry
from .scope_record_parser import OWNER, REPAIR_HINT, SCOPES, record_of, records_of  # noqa: F401

DECLARED_SCOPE_FMT = "issue-{issue}.declared-scope.jsonl"


def ledger_path(issue, repo_root, *, create=False):
    """Issue に対応する原本パスを返す。置き場は固定 dirfd で検査する。"""
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise paths.KartePathError(f"repo-root がディレクトリでない: {root}")
    path = root / "tmp" / "_karte" / DECLARED_SCOPE_FMT.format(issue=paths.validate_issue(issue))
    with open_scope_directory(path, create=create):
        return path


def has_regular_file(path) -> bool:
    """通常ファイルが存在すれば True、不在なら False、通常ファイル以外は KartePathError。"""
    with open_scope_directory(path) as directory:
        return scope_entry(path, directory) is not None


def exists(issue, repo_root) -> bool:
    """この Issue に原本があるか（置き場が無ければ無い）。"""
    try:
        path = ledger_path(issue, repo_root)
        return has_regular_file(path)
    except paths.KarteMissing:
        return False


def read_records(issue, repo_root):
    """``[(line, (round, id, scope, by))]``。1 行でも壊れていれば KarteFormatError。"""
    try:
        path = ledger_path(issue, repo_root)
    except paths.KarteMissing:
        return []
    with open_scope_directory(path) as directory:
        return records_of(path, issue, read_scope_text(path, directory))


def append_lines(issue, repo_root, new_lines, *, records=None) -> None:
    """読取時の原本が変わっていないことを検査し、原子的に追記する。"""
    path = ledger_path(issue, repo_root, create=True)
    with open_scope_directory(path) as directory:
        current = read_scope_text(path, directory)
        if records is None:
            records = records_of(path, issue, current)
        previous = [line for line, _record in records]
        if [line for line in (current or "").splitlines() if line.strip()] != previous:
            raise paths.KartePathError(f"申告 scope の原本が操作中に変更された: {path}")
        lines = previous + list(new_lines)
        write_scope_text(path, directory, "\n".join(lines) + "\n", expected=current)
