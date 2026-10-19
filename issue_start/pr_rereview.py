"""旧PRのfixer終了後に限るtrusted read-only再レビュー入力。"""
import hashlib
from pathlib import Path
import subprocess

from . import worktree_ledger
from codex_worktree_exec.source_snapshot import verify_untracked_sources
from codex_worktree_exec.errors import CodexExecError
from .gate_markers import _marker_payload
from .gate_support import IssueStartError, _BRANCH, _OID, _REPOSITORY
from .legacy_pr_evidence import validate_legacy_pr

MARKER = "ISSUE_PR_REREVIEW_V1="
PHASE_AUTHORS = {"ac-designer", "change-planner", "test-writer"}


def validate_pr_rereview(tool_input, transport, cwd, runner=subprocess.run):
    """PRを検証し、新工程履歴を持たない最新fixerの解放receiptへ束縛する。"""
    try:
        raw = _marker_payload(tool_input, transport, MARKER)
        if set(raw) != {"repository", "issue", "pr", "branch_name", "expected_oid",
                        "fixer_entry_id", "receipt_sha256"}:
            raise ValueError("PR re-review fields mismatch")
        if any(not isinstance(raw[k], int) or isinstance(raw[k], bool) or raw[k] < 1
               for k in ("issue", "pr")):
            raise ValueError("issue/PR must be positive integer")
        for key, pattern in (("repository", _REPOSITORY), ("branch_name", _BRANCH), ("expected_oid", _OID)):
            if not isinstance(raw[key], str) or not pattern.fullmatch(raw[key]):
                raise ValueError(f"invalid {key}")
        cwd = Path.cwd() if cwd is None else Path(cwd)
        root = worktree_ledger.main_worktree_root(cwd)
        entries = [entry for entry in worktree_ledger.read_ledger(root)["entries"]
                   if entry.get("branch_name") == raw["branch_name"]]
        if any(entry["agent_type"] in PHASE_AUTHORS for entry in entries):
            raise ValueError("phase author history requires normal phase approval")
        if not entries or entries[-1]["entry_id"] != raw["fixer_entry_id"]:
            raise ValueError("fixer must be latest branch owner")
        entry = entries[-1]
        if (entry["issue"] != raw["issue"] or entry["agent_type"] != "issue-fixer"
                or entry["status"] != "released" or not entry.get("closed_at")):
            raise ValueError("fixer must be stopped, collected and released")
        relative = Path(entry.get("collected_to") or "")
        if relative.is_absolute() or ".." in relative.parts or relative.parts[:3] != ("tmp", "_handoff", "collected"):
            raise ValueError("collected fixer receipt path invalid")
        receipt = root / relative
        if any(parent.is_symlink() for parent in (receipt, *receipt.parents)):
            raise ValueError("collected fixer receipt symlink")
        if hashlib.sha256(receipt.read_bytes()).hexdigest() != raw["receipt_sha256"]:
            raise ValueError("collected fixer receipt digest mismatch")
        verify_untracked_sources(cwd)
        validate_legacy_pr(raw, cwd, runner)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, worktree_ledger.LedgerError, CodexExecError, subprocess.SubprocessError) as error:
        raise IssueStartError("ISSUE_START_PR_REREVIEW_INVALID", str(error)) from None
