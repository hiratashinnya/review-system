"""検証済み申し送りの無進捗計数からの除外判定。"""

import re

from .finding_handoff_hash import content_hash
from .finding_handoff_target import REPO, normalize_target


def is_stall_exempt(finding) -> bool:
    record = finding.handoff
    if not (finding.status == "open" and finding.harm == "none"
            and finding.disposition == "deferred" and record and record.handoff_state == "verified"):
        return False
    match = re.fullmatch(rf"({REPO})#([1-9][0-9]*)", record.handoff_issue, re.ASCII)
    if not match:
        return False
    try:
        digest = content_hash(finding.id, finding.harm, finding.summary, finding.locus, finding.expected)
    except (TypeError, ValueError):
        return False
    return (record.handoff_content_hash == digest
            and normalize_target(finding.deferred_to, match.group(1)) == record.handoff_issue)
