"""レビューレポートの各ブロックに finding ID を割り当て、取り込める指摘と拒否理由を集める。"""

from . import ingest_checks, model


def _assign_id(karte, issue, item, next_seq, errors):
    """(finding_id, is_new, next_seq)。割り当てられなければ finding_id は None。"""
    if item.finding_id is None:
        return model.format_finding_id(issue, next_seq), True, next_seq + 1
    _issue_of_id, seq = model.parse_finding_id(item.finding_id)
    if karte.finding(item.finding_id) is not None:
        return item.finding_id, False, next_seq
    if seq == next_seq:
        return item.finding_id, True, next_seq + 1
    errors.append(
        f"{item.lineno} 行目: 未知の finding ID: {item.finding_id}"
        f"（台帳に無く、次に採番できるのは {model.format_finding_id(issue, next_seq)}）"
    )
    return None, False, next_seq


def collect_accepted(karte, review, issue, errors) -> list:
    """取り込む ``(finding_id, ReviewFinding, is_new)`` の列を返し、拒否理由は ``errors`` へ足す。"""
    accepted: list = []
    seen: set = set()
    next_seq = karte.next_seq()
    for item in review:
        finding_id, is_new, next_seq = _assign_id(karte, issue, item, next_seq, errors)
        if finding_id is None:
            continue
        if finding_id in seen:
            errors.append(f"{item.lineno} 行目: finding ID がレポート内で重複している: {finding_id}")
            continue
        seen.add(finding_id)
        bad_refs = ingest_checks.invalid_distinct_refs(karte, seen, finding_id, item)
        if bad_refs:
            errors.extend(bad_refs)
            continue
        if is_new:
            duplicate = ingest_checks.find_duplicate(karte, accepted, item)
            if duplicate is not None:
                errors.append(
                    f"{item.lineno} 行目: ID 再発番を検出: {finding_id} は既存の未解消 "
                    f"{duplicate} と同一の指摘（locus が交差し summary が一致）。"
                    "未解消の指摘を再度挙げるときは同じ ID を再利用すること"
                    f"（別物なら当該ブロックに `distinct_from: {duplicate}` を書いて名指しする）"
                )
                continue
        accepted.append((finding_id, item, is_new))
    return accepted
