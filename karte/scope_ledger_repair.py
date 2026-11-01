"""壊れた申告 scope の原本を復旧する（主文脈専用の ``activate --repair-declared-scope`` から呼ぶ）。"""

from . import paths
from .scope_records import ledger_path, record_of

BACKUP_SUFFIX = ".bak"


def _free_backup_path(path):
    """既存のバックアップを上書きしない：``.bak``、``.bak.1``、``.bak.2`` … の最初の空き。"""
    candidate = path.with_name(path.name + BACKUP_SUFFIX)
    generation = 0
    while candidate.exists():
        generation += 1
        candidate = path.with_name(f"{path.name}{BACKUP_SUFFIX}.{generation}")
    return candidate


def repair(issue, repo_root) -> list:
    """壊れた行を除いて書き直し、除いた行を返す。元のファイルは世代を分けて ``.bak*`` に残す。"""
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
        paths.write_text_atomic(_free_backup_path(path), original)
        paths.write_text_atomic(path, "\n".join(kept) + "\n" if kept else "")
    return dropped
