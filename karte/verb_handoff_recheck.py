"""記録済み申し送りを再観測する。"""
import re
from dataclasses import replace

from . import finding_handoff_context as context, finding_handoff_github as github
from .finding_handoff_errors import FindingHandoffError
from .finding_handoff_observe import describe, timestamp, verify
from .finding_handoff_store import snapshot, store
from .finding_handoff_target import REPO
from .verb_boundary import fail_close


def observe(finding, repository):
    record = finding.handoff
    match = re.fullmatch(rf"({REPO})#([1-9][0-9]*)", record.handoff_issue, re.ASCII)
    if not match or match.group(1).lower() != repository.lower():
        raise FindingHandoffError("repository", "記録の repository が origin と一致しません")
    context.issue_status(record.handoff_issue)
    verify(record.handoff_issue, record.handoff_comment_url, finding,
           github.current_login(), record.handoff_content_hash)


@fail_close(locked=False)
def cmd_handoff_recheck(args, repo_root, now=None):
    issue_id, karte = context.load(args, repo_root)
    repository = context.origin()
    findings = ([context.require_finding(karte, item) for item in args.finding]
                if args.finding else [item for item in karte.findings if item.handoff])
    failed = False
    for finding in findings:
        if not finding.handoff:
            print(f"{finding.id}: handoff 記録がありません")
            failed = True
            continue
        observed = snapshot(finding)
        try:
            observe(finding, repository)
            record = replace(finding.handoff, handoff_state="verified", handoff_verified_at=timestamp(now))
            message = "verified"
        except FindingHandoffError as exc:
            record = replace(finding.handoff, handoff_state="invalid")
            message, failed = describe(exc), True
        try:
            store(repo_root, issue_id, finding.id, observed, record)
        except FindingHandoffError as exc:
            message, failed = describe(exc), True
        print(f"{finding.id}: {message}")
    return 4 if failed else 0
