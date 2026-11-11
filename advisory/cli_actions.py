"""Write command adapter; readers and state machine live elsewhere."""

from pathlib import Path

from .operations import modify, new


def write_action(args) -> dict:
    root = Path(args.root)
    if args.action == "new":
        key, sha = new(root, args.base_ref, topic=args.topic,
                       created_on=args.created_on, sources=args.source,
                       evidence=args.evidence, recommendation=args.recommendation,
                       triage_rationale=args.triage_rationale,
                       policy_version=args.policy_version,
                       duplicate_reason=args.distinct_reason,
                       related_ids=args.related, at=args.at)
        return {"id": key, "sha256": sha}
    if args.action == "amend":
        mapping = {"evidence": args.evidence,
                   "recommendation": args.recommendation,
                   "triage_rationale": args.triage_rationale,
                   "policy_version": args.policy_version,
                   "duplicate_reason": args.distinct_reason,
                   "sources": args.source, "related_ids": args.related}
        changes = {key: value for key, value in mapping.items() if value is not None}
    elif args.action == "transition":
        changes = {"status": args.to}
    elif args.action == "promote":
        changes = {"promoted_issue": args.existing_issue}
    else:
        raise ValueError("unknown write action")
    value = modify(root, args.base_ref, args.id, args.expected_sha256,
                   args.action, at=args.at, reason=args.reason, changes=changes)
    return {"id": args.id, "sha256": value}
