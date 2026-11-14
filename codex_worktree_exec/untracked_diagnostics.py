"""One deterministic categorized diagnostic instead of first-hit failure."""
from collections import defaultdict

HINTS = {
    "unsafe_path": "Inspect symlink, directory or nonregular path",
    "foreign_cache": "Trusted caller: python3 -m codex_worktree_exec.cache_prune --apply",
    "stale_cache": "Trusted caller: python3 -m codex_worktree_exec.cache_prune --apply",
    "unsafe_cache": "Inspect source/cache; trusted caller may run cache_prune --apply",
    "unsupported_cache_format": "Trusted caller: python3 -m codex_worktree_exec.untracked_recovery --apply (quarantine .pyo)",
    "coverage_output": "Trusted caller: python3 -m codex_worktree_exec.untracked_recovery --apply",
    "tool_state": "Trusted caller: python3 -m codex_worktree_exec.untracked_recovery --apply; preserved in quarantine",
    "unapproved_tmp": "Trusted caller: inspect then run python3 -m codex_worktree_exec.untracked_recovery --apply",
    "unapproved_source": "Commit or approve source; gitignore is not authorization",
}


def describe(violations: list[tuple[str, str]]) -> str:
    groups = defaultdict(list)
    for category, path in violations:
        groups[category].append(path)
    sections = []
    for category in sorted(groups):
        paths = sorted(groups[category])
        examples = ", ".join(paths[:3])
        sections.append(f"{category} count={len(paths)} examples=[{examples}] "
                        f"recovery=[{HINTS[category]}]")
    return "untracked source outside tmp inputs/outputs: " + "; ".join(sections)
