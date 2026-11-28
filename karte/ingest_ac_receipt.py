"""Obtain AC provenance for an accepted reviewer round, not from user CLI args."""
from . import ac_snapshot_binding
from .active_pointer import read_active


def accepted(repo_root, issue, round_no, report, policy):
    if policy is None or not policy.record_declarations:
        return None
    # Revalidate inside the ingest writer lock, even if reviewer_cli already did.
    ac_snapshot_binding.validate(repo_root, issue, round_no, report)
    return read_active(repo_root, required=True)["ac_snapshot"]
