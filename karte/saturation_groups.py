from __future__ import annotations

from . import model, similarity


def view_of(karte: model.Karte, attempt: model.Attempt) -> similarity.AttemptView:
    return similarity.AttemptView(
        number=attempt.number,
        root_cause=attempt.root_cause,
        change_kind=attempt.change_kind,
        targets=tuple(attempt.targets),
        touched=tuple(karte.touched_of(attempt.number)),
    )


def priors_for(karte: model.Karte, finding_ids) -> list:
    """``finding_ids`` のうち **未解消** のものを共有する過去 Attempt の投影を返す。"""
    open_ids = karte.open_ids()
    relevant = {fid for fid in finding_ids if fid in open_ids}
    views = []
    for attempt in karte.attempts:
        if relevant & set(attempt.finding_ids):
            views.append(view_of(karte, attempt))
    return views

def saturated_groups(karte: model.Karte) -> list:
    """append と同じ判定で飽和したアプローチを列挙する。"""
    open_ids = karte.open_ids()
    relevant = [
        attempt for attempt in karte.attempts if open_ids & set(attempt.finding_ids)
    ]
    groups: list = []
    seen: set = set()
    for attempt in relevant:
        candidate = similarity.AttemptView(
            number=attempt.number,
            root_cause=attempt.root_cause,
            change_kind=attempt.change_kind,
            targets=tuple(attempt.targets),
            touched=(),
        )
        # `append` と同じ入力集合（候補の finding_ids でスコープした priors）を使う。
        priors = priors_for(karte, attempt.finding_ids)
        hits = similarity.find_hits(candidate, priors)
        if not similarity.is_saturated(hits):
            continue
        members = tuple(sorted({hit.prior for hit in hits}))
        if members in seen:
            continue
        seen.add(members)
        groups.append((attempt.number, list(members), hits, candidate))
    return groups


def group_directive(karte: model.Karte, candidate_number: int, hits, candidate) -> str:
    """飽和したアプローチの転換指令（``render`` / ``close-attempt`` の表示用）。"""
    attempt = karte.attempt(candidate_number)
    open_ids = karte.open_ids() & set(attempt.finding_ids if attempt else [])
    return similarity.build_directive(
        candidate, hits, open_ids, subject_label="飽和したアプローチ"
    ).text()

