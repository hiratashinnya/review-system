"""Capture an actual read-only reviewer execution for a future triage binding."""

import hashlib
import hmac
import json
import tempfile
from pathlib import Path

from finding_triager.approved_materials import approved_materials
from .invocation import build_codex_argv, compose_prompt
from .launcher import run_codex
from .nesting_guard import refuse_nested_launch
from .profile_pin import verify_profile_pinned
from .project_trust import codex_home, verify_project_trusted
from .prompt_files import read_prompt
from .worktree_binding import bind_worktree

DOMAIN = b"finding-triage-review-capture/v1\0"


def capture_reviewer(request, cwd, marker, environ, codex, key):
    """Run and attest only a real reviewer child; do not write the review ledger.

    The caller, marker and key are trusted; never pass the key to the child.
    This receipt alone does not attest Issue AC, change base, or triage readiness.
    """
    if request.role != "pr-reviewer" or not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("review role and trusted capture key required")
    refuse_nested_launch(environ)
    worktree = bind_worktree(request.worktree, Path(cwd))
    verify_profile_pinned(worktree, "pr-reviewer")
    verify_project_trusted(worktree, codex_home(environ))
    if request.binding_file is None or Path(marker["binding_file"]) != request.binding_file:
        raise ValueError("reviewer binding mismatch")
    before = approved_materials(worktree, marker)
    prompt = compose_prompt("pr-reviewer", worktree, read_prompt(request.prompt_file, cwd, worktree))
    with tempfile.TemporaryDirectory(prefix="triage-review-", dir=worktree / "tmp") as directory:
        output = Path(directory) / "output.md"
        status = run_codex(build_codex_argv(request, worktree, output, codex), prompt,
                           cwd=worktree, timeout_seconds=request.timeout_seconds,
                           environ=environ, quiet=True)
        if status or not output.is_file() or output.is_symlink():
            raise ValueError("reviewer execution failed")
        body = output.read_bytes()
        if not body.strip():
            raise ValueError("reviewer output empty")
        body.decode("utf-8")
        after = approved_materials(worktree, marker)
        if before != after:
            raise ValueError("approval or materials changed during reviewer execution")
    receipt = {"schema": "finding-triage-review-capture/v1", "producer": "pr-reviewer",
               "worktree": str(worktree), "review_sha256": hashlib.sha256(body).hexdigest(),
               "approval": before}
    raw = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return body, raw, hmac.new(key, DOMAIN + raw, hashlib.sha256).hexdigest()
