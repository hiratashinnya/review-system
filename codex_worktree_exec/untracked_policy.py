"""Issue #655: fail-closed classification of ignored and untracked inputs."""
import importlib.util
import subprocess
from pathlib import Path
from .compiled_cache import verify_compiled_cache

LOCKS = frozenset({".ai/feedback/.writer.lock", ".claude/scheduled_tasks.lock",
                   "tmp/_worktree/ledger.json.lock", "tmp/_karte/.writer.lock",
                   "issue_start/adr/.write.lock", "issue_start/adr/.file-issue.lock"})
TMP_DATA = frozenset({".json", ".md", ".yaml", ".yml", ".txt", ".log"})


def regular_unlinked(path: Path) -> bool:
    return path.is_file() and not any(p.is_symlink() for p in (path, *path.parents))


def orphan_cache(path: Path, root: Path) -> bool:
    if path.parent.name != "__pycache__" or path.suffix != ".pyc":
        return False
    try:
        source = Path(importlib.util.source_from_cache(str(path)))
        relative = source.relative_to(root.resolve()).as_posix()
    except (ValueError, IndexError):
        return False
    if source.exists() or source.is_symlink():
        return False
    prefix = ["git", "-C", str(root)]
    committed = subprocess.run(prefix + ["ls-tree", "-r", "--name-only", "HEAD",
                                         "--", relative], capture_output=True, check=True)
    indexed = subprocess.run(prefix + ["ls-files", "--cached", "--", relative],
                             capture_output=True, check=True)
    return not committed.stdout and not indexed.stdout


def classify_untracked(root: Path, name: str, source_cache: dict) -> str | None:
    path = root / name
    if not regular_unlinked(path):
        return "unsafe_path"
    if name in LOCKS:
        return None
    parts = Path(name).parts
    if parts and parts[0] == "tmp" and path.suffix in TMP_DATA:
        return None
    if "__pycache__" in parts and path.suffix == ".pyo":
        return "unsupported_cache_format"
    if "__pycache__" in parts and path.suffix == ".pyc":
        if orphan_cache(path, root):
            return None
        try:
            verify_compiled_cache(path, root, source_bytes=source_cache)
            return None
        except ValueError as error:
            reason = str(error)
            if "tag/optimization" in reason:
                return "foreign_cache"
            if "does not match" in reason or "source changed" in reason:
                return "stale_cache"
            return "unsafe_cache"
    if name == ".coverage" or name.startswith("htmlcov/"):
        return "coverage_output"
    if name.startswith(".serena/"):
        return "tool_state"
    if parts and parts[0] == "tmp":
        return "unapproved_tmp"
    return "unapproved_source"
