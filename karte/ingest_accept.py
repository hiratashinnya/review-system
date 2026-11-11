"""レビューレポートの各ブロックに finding ID を割り当て、取り込める指摘と拒否理由を集める。"""

from . import ingest_checks, model
from .ingest_types import AcceptedFinding, Assigned, CollectResult, Rejected


def _assign_id(karte, issue, item, next_seq):
    """``Assigned`` か、ID を割り当てられない場合の ``Rejected``。"""
    if item.finding_id is None:
        return Assigned(model.format_finding_id(issue, next_seq), True, next_seq + 1)
    _issue_of_id, seq = model.parse_finding_id(item.finding_id)
    if karte.finding(item.finding_id) is not None:
        return Assigned(item.finding_id, False, next_seq)
    if seq == next_seq:
        return Assigned(item.finding_id, True, next_seq + 1)
    return Rejected(
        f"{item.lineno} 行目: 未知の finding ID: {item.finding_id}"
        f"（台帳に無く、次に採番できるのは {model.format_finding_id(issue, next_seq)}）",
        next_seq,
    )


def _duplicate_error(item, finding_id, duplicate) -> str:
    return (
        f"{item.lineno} 行目: ID 再発番を検出: {finding_id} は既存の未解消 "
        f"{duplicate} と同一の指摘（locus が交差し summary が一致）。"
        "未解消の指摘を再度挙げるときは同じ ID を再利用すること"
        f"（別物なら当該ブロックに `distinct_from: {duplicate}` を書いて名指しする）"
    )


def collect_accepted(karte, review, issue) -> CollectResult:
    """取り込む指摘の列と、拒否理由の列を返す。"""
    accepted: list = []
    errors: list = []
    seen: set = set()
    next_seq = karte.next_seq()
    for item in review:
        assignment = _assign_id(karte, issue, item, next_seq)
        next_seq = assignment.next_seq
        if isinstance(assignment, Rejected):
            errors.append(assignment.message)
            continue
        finding_id = assignment.finding_id
        if finding_id in seen:
            errors.append(f"{item.lineno} 行目: finding ID がレポート内で重複している: {finding_id}")
            continue
        seen.add(finding_id)
        bad_refs = ingest_checks.invalid_distinct_refs(karte, seen, finding_id, item)
        if bad_refs:
            errors.extend(bad_refs)
            continue
        if assignment.is_new:
            duplicate = ingest_checks.find_duplicate(karte, accepted, item)
            if duplicate is not None:
                errors.append(_duplicate_error(item, finding_id, duplicate))
                continue
        accepted.append(AcceptedFinding(finding_id, item, assignment.is_new))
    return CollectResult(accepted, errors)
