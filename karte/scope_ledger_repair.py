"""壊れた申告 scope の原本を復旧する（主文脈専用の ``activate --repair-declared-scope`` から呼ぶ）。"""

from . import paths
from .scope_ledger import BACKUP_SUFFIX, ledger_path, record_of


def repair(issue, repo_root) -> list:
    """壊れた行を除いて書き直し、除いた行を返す。元のファイルは ``.bak`` に残す。"""
    try:
        path = ledger_path(issue, repo_root)
    except paths.KarteMissing:
        return []
    if not path.is_file():
        return []
    original = paths.read_text(path)
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
        paths.write_text_atomic(path.with_name(path.name + BACKUP_SUFFIX), original)
        paths.write_text_atomic(path, "\n".join(kept) + "\n" if kept else "")
    return dropped
