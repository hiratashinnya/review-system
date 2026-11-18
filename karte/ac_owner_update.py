"""Owner-only guarded AC checkbox update entry. Never call from reviewer."""
import argparse
import sys
from pathlib import Path

from . import ac_owner_evidence, ac_owner_github, paths
from .ac_check_update import plan, verify_written
from .errors import KarteUsageError
from .format_error import KarteFormatError


def perform(repo_root, issue, round_no, snapshot_source, repository, *,
            dry_run=False, remote=None):
    """Only this path may issue the automatic AC-check PATCH."""
    issue = paths.validate_issue(issue)
    remote = ac_owner_github.issue if remote is None else remote
    snapshot, decisions = ac_owner_evidence.require_trusted_round(
        repo_root, issue, round_no, snapshot_source,
    )
    original = remote(repository, issue)
    updated, changed = plan(snapshot, original, decisions)
    if not changed or dry_run:
        return changed
    # Read again immediately before writing; API has no atomic CAS guarantee.
    if remote(repository, issue) != original:
        raise KarteUsageError("Issue本文が書込直前に変化したためAC更新を中止")
    remote(repository, issue, new_body=updated)
    # A failed read-back may mean a write occurred: report failure, do not retry.
    verify_written(updated, remote(repository, issue))
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="主文脈専用: 受理済みclean roundでのみGitHub IssueのACチェックを更新"
    )
    parser.add_argument("--issue", required=True)
    parser.add_argument("--round", required=True)
    parser.add_argument("--repository", required=True, help="owner/name")
    parser.add_argument("--snapshot-source", required=True, help="activate出力の凍結原本source")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        # Reject noncanonical integers rather than silently normalizing an Issue.
        issue = paths.validate_issue(args.issue)
        if not args.round.isascii() or not args.round.isdecimal() or args.round.startswith("0"):
            raise KarteUsageError("roundは1以上のASCII整数")
        round_no = int(args.round)
        if round_no < 1:
            raise KarteUsageError("roundは1以上のASCII整数")
        root = Path(args.repo_root).resolve()
        changes = perform(root, issue, round_no, args.snapshot_source,
                          args.repository, dry_run=args.dry_run)
    except (KarteUsageError, KarteFormatError, paths.KartePathError, OSError) as exc:
        print(f"拒否（fail-close）: {exc}", file=sys.stderr)
        return 4
    status = "dry-run" if args.dry_run else "read-back検証済み"
    print(f"=== owner AC checkbox {status} ===")
    print("  変更対象AC: " + (", ".join(map(str, changes)) if changes else "(なし)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
