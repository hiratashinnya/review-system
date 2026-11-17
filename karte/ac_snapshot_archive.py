"""Immutable per-activation snapshots, including cancelled/retried review rounds."""

from hashlib import sha256
from pathlib import Path
import re

from . import paths
from .errors import KarteUsageError


def _archive(repo_root, issue, round_no, suffix=None, *, create=False):
    directory = paths.karte_dir(repo_root, create=create)
    name = f"issue-{issue}-ac-round-{round_no}"
    if suffix is not None:
        name += f"-{suffix}"
    return paths.resolve_within_repo(directory / (name + ".md"), repo_root)


def path_for_stage(repo_root, issue, round_no, body):
    """Use the complete Issue body hash, not only the AC digest."""
    suffix = sha256(body.encode("utf-8")).hexdigest()
    return _archive(repo_root, issue, round_no, suffix, create=True)


def path_for_record(repo_root, issue, round_no, record):
    """Trust only the canonical round path, never a caller-chosen pointer path."""
    source = record.get("source")
    if not isinstance(source, str):
        raise KarteUsageError("AC snapshotの保存先が不正")
    prefix = f"issue-{issue}-ac-round-{round_no}"
    match = re.fullmatch(re.escape(prefix) + r"(?:-([0-9a-f]{64}))?\.md", Path(source).name)
    if match is None:
        raise KarteUsageError("AC snapshotの保存先が不正")
    suffix = match.group(1)
    path = _archive(repo_root, issue, round_no, suffix)
    if source != str(path.relative_to(Path(repo_root).resolve())):
        raise KarteUsageError("AC snapshotの保存先が不一致")
    if suffix is not None and sha256(paths.read_text(path).encode("utf-8")).hexdigest() != suffix:
        raise KarteUsageError("AC snapshotの保存内容が原本digestと不一致")
    return path
