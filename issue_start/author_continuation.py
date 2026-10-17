"""前作者の回収・解放済みreceiptとremote先端を次作者へ束縛する。"""
import hashlib
from pathlib import Path
import subprocess

from . import worktree_ledger
from .gate_git import _git_output
from .gate_markers import _marker_payload
from .gate_support import IssueStartError

PREDECESSORS = {"change-planner": "ac-designer", "test-writer": "change-planner",
                "issue-implementer": "test-writer"}
MARKER = "ISSUE_PHASE_PREDECESSOR_V1="


def validate_author_continuation(tool_input, transport, ack, cwd, runner=subprocess.run):
    """6field bindingを変更せず、trusted caller指定の回収receiptを検査する。"""
    if ack.agent_type not in PREDECESSORS:
        return
    try:
        raw = _marker_payload(tool_input, transport, MARKER)
        if set(raw) != {"entry_id", "receipt_sha256"}:
            raise ValueError("predecessor fields mismatch")
        root = worktree_ledger.main_worktree_root(Path.cwd() if cwd is None else Path(cwd))
        entries = worktree_ledger.read_ledger(root)["entries"]
        candidates = [entry for entry in entries if entry.get("issue") == ack.issue
                      and entry.get("branch_name") == ack.branch_name]
        if not candidates or candidates[-1]["entry_id"] != raw["entry_id"]:
            raise ValueError("predecessor must be latest branch owner")
        entry = candidates[-1]
        if (entry["agent_type"] != PREDECESSORS[ack.agent_type]
                or entry["status"] != "released" or not entry.get("closed_at")):
            raise ValueError("predecessor not stopped, collected and released")
        relative = Path(entry.get("collected_to") or "")
        if relative.is_absolute() or ".." in relative.parts or relative.parts[:3] != ("tmp", "_handoff", "collected"):
            raise ValueError("collected receipt path invalid")
        receipt = root / relative
        if any(parent.is_symlink() for parent in (receipt, *receipt.parents)):
            raise ValueError("collected receipt symlink")
        if hashlib.sha256(receipt.read_bytes()).hexdigest() != raw["receipt_sha256"]:
            raise ValueError("collected receipt digest mismatch")
        ref = f"refs/heads/{ack.branch_name}"
        output = _git_output(["git", "ls-remote", "--exit-code",
                              f"https://github.com/{ack.repository}.git", ref],
                             cwd=root, runner=runner, reason="ISSUE_START_CONTINUATION_INVALID")
        if output.strip().split() != [ack.expected_oid, ref]:
            raise ValueError("remote exact OID mismatch")
    except (OSError, ValueError, TypeError, KeyError, worktree_ledger.LedgerError) as error:
        raise IssueStartError("ISSUE_START_CONTINUATION_INVALID", str(error)) from None
