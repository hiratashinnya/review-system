"""Contract/protected incoming changes require a new trusted launch, never a bypass."""

import os
from .base_error import require
from .base_git import git


def protected(path):
    return path.startswith((".git/", ".codex/", ".agents/", ".claude/")) or path in {
        "AGENTS.md", "CLAUDE.md", ".ai/agents/issue-fixer.md"}


def reject_protected_incoming(workspace, head, base):
    common = git(workspace, "merge-base", head, base).stdout.strip().decode("ascii")
    paths = git(workspace, "diff", "--name-only", "--no-renames", "-z", common, base).stdout
    rejected = sorted(os.fsdecode(raw) for raw in paths.split(b"\0") if raw and protected(os.fsdecode(raw)))
    require(not rejected, "BASE_PROTECTED_INCOMING_STOP: " + ", ".join(rejected))
