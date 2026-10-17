"""path_ref宣言に従って実在資産とHEADのbytesを束縛する。"""
import subprocess
from pathlib import Path
from feedback_ledger.paths import FeedbackPathError, resolve_within_repo
from .schema import SPECS


def committed_bytes(repo, candidate):
    root = Path(repo).resolve()
    if Path(candidate).is_absolute():
        raise ValueError(f"repo相対pathが必要: {candidate}")
    target = resolve_within_repo(candidate, root)
    if not target.is_file():
        raise ValueError(f"実在しない資産path: {candidate}")
    name = target.relative_to(root).as_posix()
    entry = subprocess.run(["git", "ls-tree", "HEAD", "--", name], cwd=root,
                           capture_output=True, check=False)
    if entry.returncode or entry.stdout.split(b" ", 1)[0] not in (b"100644", b"100755"):
        raise ValueError(f"HEADの通常ファイルでない資産: {candidate}")
    result = subprocess.run(["git", "show", f"HEAD:{name}"], cwd=root,
                            capture_output=True, check=False)
    if result.returncode or result.stdout != target.read_bytes():
        raise ValueError(f"未commitまたはHEADから改変された資産: {candidate}")
    return result.stdout


def path_errors(repo, data):
    errors = []
    for table, field in SPECS[data["artifact_type"]].field_map().values():
        if not field.path_ref:
            continue
        sections = data.get(table.name, []) if table.repeated else [data]
        for section in sections:
            value = section[field.name]
            for candidate in value if isinstance(value, list) else [value]:
                try:
                    committed_bytes(repo, candidate)
                except (ValueError, OSError, FeedbackPathError) as exc:
                    errors.append(f"{data['id']}::{field.name}: {exc}")
    return errors
