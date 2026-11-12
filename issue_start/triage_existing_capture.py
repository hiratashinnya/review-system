"""Capture the normal trusted reviewer execution without running another reviewer."""
import json
import subprocess
from pathlib import Path

from codex_worktree_exec.prompt_files import resolve_output_target
from codex_worktree_exec.triage_binding_capture import binding_from_capture
from codex_worktree_exec.triage_review_capture import capture_existing
from finding_triager.approved_materials import approved_materials


def _head(root):
    return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()


def execute_with_capture(request, args, root, marker, key, pr, phase, round_no, output, execute):
    if request.role != "pr-reviewer" or len(key) < 32:
        raise ValueError("trusted reviewer and capture key required")
    target = resolve_output_target(Path(output), root, root)
    review_output = resolve_output_target(request.output_file, root, root)
    if target.exists() or review_output.exists() or target == review_output:
        raise ValueError("capture and review outputs must be new and distinct")
    before = approved_materials(root, marker)
    oid = _head(root)
    status = execute(args, cwd=root)
    if status:
        return status
    if review_output.is_symlink() or not review_output.is_file():
        raise ValueError("normal reviewer output missing")
    body = review_output.read_bytes()
    after = approved_materials(root, marker)
    if before != after or oid != _head(root):
        raise ValueError("review approval or HEAD changed during execution")
    captured = capture_existing(body, root, before, oid, key)
    binding = binding_from_capture(*captured, root, key, pr=pr, phase=phase, round_no=round_no)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(binding, stream, ensure_ascii=False)
    return 0
