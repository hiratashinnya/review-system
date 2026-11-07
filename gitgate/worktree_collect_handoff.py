"""Read and verify a handoff before marking it collected or removing anything."""

import hashlib
from .worktree_models import WorktreeError
from .worktree_path_validation import resolve_within
from .worktree_handoff_paths import HANDOFF_DIR_PARTS, validate_handoff_relpath, validate_collect_dest
from .worktree_config import COLLECTED_DIRNAME
from .worktree_handoff_io import _ensure_collected_dir

def collect_handoff(repo_root, *, entry, relative_worktree, handoff_path, into,
                    allow_missing_handoff, max_bytes, resolved_entry_id,
                    collected_to, read_handoff, write_collected):
    relative_handoff = handoff_path
    if relative_handoff is None and entry is not None:
        relative_handoff = entry.get("handoff_path")
    if not relative_handoff:
        if not allow_missing_handoff:
            raise WorktreeError(
                "COLLECT_HANDOFF_UNKNOWN",
                "handoff の相対パスが判らない（--handoff か --allow-missing-handoff が要る）",
            )
    else:
        expected_issue = entry.get("issue") if entry is not None else None
        relative_handoff = validate_handoff_relpath(
            relative_handoff, expected_issue=expected_issue
        )

    worktree_dir = resolve_within(repo_root, relative_worktree)

    data: bytes | None = None
    if relative_handoff:
        source = resolve_within(
            worktree_dir, relative_handoff, error="COLLECT_HANDOFF_SYMLINK"
        )
        if not source.exists():
            if not allow_missing_handoff:
                raise WorktreeError("COLLECT_HANDOFF_MISSING", str(source))
        else:
            data = _read_handoff(source, max_bytes=max_bytes)
            if len(data) > max_bytes:
                raise WorktreeError("COLLECT_HANDOFF_TOO_LARGE", str(max_bytes))

    if data is not None:
        if into is not None:
            relative_dest = validate_collect_dest(into)
        else:
            key = resolved_entry_id or relative_worktree.rsplit("/", 1)[-1]
            basename = relative_handoff.rsplit("/", 1)[-1]
            relative_dest = "/".join(
                (*HANDOFF_DIR_PARTS, COLLECTED_DIRNAME, f"{key}--{basename}")
            )
        parent_rel, _, filename = relative_dest.rpartition("/")
        directory = _ensure_collected_dir(repo_root, parent_rel)
        dest = directory / filename
        if dest.is_symlink():
            raise WorktreeError("COLLECT_DEST_SYMLINK", str(dest))
        _write_collected(dest, data)
        expected_digest = hashlib.sha256(data).hexdigest()
        actual_digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        if actual_digest != expected_digest:
            try:
                dest.unlink()
            except OSError:
                pass
            raise WorktreeError(
                "COLLECT_VERIFY_MISMATCH",
                f"{relative_dest}: expected {expected_digest}; actual {actual_digest}",
            )
        collected_to = relative_dest

    return collected_to, data is None
