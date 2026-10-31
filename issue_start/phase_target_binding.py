"""工程承認、native取得対象、実検査作業面を同じIssue/repository/OIDへ束縛する。"""
import subprocess
from pathlib import Path
from .gate_git import _canonical_github_repository
from .gate_support import IssueStartError


def validate_phase_target(approval, native, cwd, *, initial=False):
    """未来branchの初回著作と、既存branchの後続著作を区別して照合する。

    後続の検査面はdetachedに限り、どのworktreeも対象branchを掴んでいないことを要求する。branch名は台帳の最新owner照合と
    remote exact OID照合（ls-remote・adopt-branch stage 2）へ委ねる（#685）。"""
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
        else:
            _require_detached(root, target["branch_name"], target["expected_oid"])
            _require_branch_unheld(git, target["branch_name"], target["expected_oid"])
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        raise IssueStartError("ISSUE_START_PHASE_TARGET_INVALID", str(error)) from None


def _require_detached(root, branch_name, expected_oid):
    """次作者のadopt-branchは対象branchを掴む作業面があると必ず拒否するので、detachedだけを許す。"""
    result = subprocess.run(["git", "-C", str(root), "symbolic-ref", "--quiet", "--short", "HEAD"],
                            capture_output=True, text=True)
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    if result.stdout.strip() != branch_name:
        raise ValueError("phase inspected branch mismatch")
    raise ValueError(f"phase inspected worktree holds target branch {branch_name}; next author's "
                     f"adopt-branch would be refused. Run `git switch --detach {expected_oid}` "
                     "in the dispatch worktree, then dispatch again")


def _require_branch_unheld(git, branch_name, expected_oid):
    """検査面以外のworktreeが掴んでいてもadoptは拒否されるので全worktreeを見る（git失敗は拒否）。"""
    target, path, holders = f"branch refs/heads/{branch_name}", None, []
    for line in git("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.strip() == target:
            holders.append(path or "<path unknown>")
    if holders:
        raise ValueError(f"worktree {', '.join(holders)} holds target branch {branch_name}; next "
                         "author's adopt-branch would be refused. Release it there first (linked: "
                         f"`git switch --detach {expected_oid}`; primary checkout: `git switch "
                         "<default branch>`; agent worktree: `python3 -m gitgate collect-worktree "
                         "--entry <entry-id>`), then dispatch again")
