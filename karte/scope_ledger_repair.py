"""壊れた申告 scope の原本を復旧する（主文脈専用の ``activate --repair-declared-scope`` から呼ぶ）。"""

from . import paths
from .scope_atomic import write_scope_backup, write_scope_text
from .scope_directory import open_scope_directory
from .scope_ledger_io import read_scope_text
from .scope_records import ledger_path, record_of

BACKUP_SUFFIX = ".bak"


def repair(issue, repo_root) -> list:
    """壊れた行を除いて書き直し、除いた行を返す。元のファイルは世代を分けて ``.bak*`` に残す。"""
    try:
        path = ledger_path(issue, repo_root)
    except paths.KarteMissing:
        return []
    with open_scope_directory(path) as directory:
        original = read_scope_text(path, directory)
        if original is None:
            return []
        kept, dropped = [], []
        for line in original.splitlines():
            if not line.strip():
                continue
            try:
                record_of(line)
                kept.append(line)
            except ValueError:
                dropped.append(line)
        if dropped:
            write_scope_backup(path, directory, original)
            write_scope_text(path, directory, "\n".join(kept) + "\n" if kept else "", expected=original)
        return dropped
