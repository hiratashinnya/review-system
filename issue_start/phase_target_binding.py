"""工程承認、native取得対象、実検査作業面を同じIssue/repository/OIDへ束縛する。"""
import subprocess
from pathlib import Path
from .gate_git import _canonical_github_repository
from .gate_support import IssueStartError


def validate_phase_target(approval, native, cwd, *, initial=False):
    """未来branchの初回著作と、既存branchの後続著作を区別して照合する。"""
    try:
        target = approval["dispatch_target"]
        if not isinstance(target, dict) or set(target) != {"repository", "branch_name", "expected_oid"}:
            raise ValueError("dispatch_target fields mismatch")
        if approval["issue"] != native["issue"]:
            raise ValueError("phase/native issue mismatch")
        expected = dict(repository=native["repository"], branch_name=native["branch_name"],
                        expected_oid=native["base_oid" if initial else "expected_oid"])
        if target != expected:
            raise ValueError("phase/native repository/branch/OID mismatch")
        if approval["_inspected_oid"] != target["expected_oid"]:
            raise ValueError("phase inspected OID/native OID mismatch")
        root = Path.cwd() if cwd is None else Path(cwd)
        def git(*args):
            return subprocess.run(["git", "-C", str(root), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        if (_canonical_github_repository(git("remote", "get-url", "origin")) != target["repository"]
                or git("rev-parse", "HEAD") != target["expected_oid"]):
            raise ValueError("phase inspected repository/HEAD mismatch")
        if initial:
            if (approval["snapshot_oid"] != target["expected_oid"]
                    or git("rev-parse", native["base_ref"]) != target["expected_oid"]):
                raise ValueError("phase inspected initial base mismatch")
        elif git("symbolic-ref", "--quiet", "--short", "HEAD") != target["branch_name"]:
            raise ValueError("phase inspected branch mismatch")
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        raise IssueStartError("ISSUE_START_PHASE_TARGET_INVALID", str(error)) from None
