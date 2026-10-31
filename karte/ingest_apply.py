"""検証を通ったレビュー指摘を台帳の finding へ反映し、取り込み結果を出力する。

設計理由は [.ai/rationale/karte-module-split.md](../.ai/rationale/karte-module-split.md)。
"""

from . import ingest_checks, model


def apply_accepted(karte, accepted, round_no) -> tuple:
    """``(created, resolved, excluded)`` を返す。"""
    created, resolved, excluded = [], [], []  # excluded＝distinct_from の除外ペア（監査用）
    for finding_id, item, _is_new in accepted:
        finding = karte.finding(finding_id)
        if finding is None:
            finding = model.Finding(id=finding_id)
            karte.findings.append(finding)
            created.append(finding_id)
        # K-06: 解消は**明示宣言**でのみ成立する（`harm` の値によらず一律）。
        finding.status = item.status
        finding.resolved_round = round_no if item.status == "resolved" else None
        if item.status == "resolved":
            resolved.append(finding_id)
        finding.harm = item.harm
        finding.harm_detail = item.harm_detail
        finding.severity = item.severity
        _apply_owner_fields(finding, item)
        finding.locus = list(item.locus)
        finding.summary = item.summary
        finding.evidence = item.evidence
        finding.expected = item.expected
        finding.recheck = item.recheck
        if round_no not in finding.rounds:
            finding.rounds.append(round_no)
        finding.rounds.sort()
        excluded.extend(f"{finding_id} ↔ {other}" for other in item.distinct_from)
    return created, resolved, excluded


def _apply_owner_fields(finding, item) -> None:
    """scope と disposition 系はレポートの値で毎ラウンド上書きする（Issue #495）。

    据え置きにすると、書かれなくなった disposition が台帳に残り続けて静かにずれる。
    書き忘れは未決定へ倒れて verdict のゲートに掛かる（fail-close）。
    """
    finding.scope = item.scope
    finding.disposition = item.disposition
    finding.deferred_to = item.deferred_to
    finding.waived_by = item.waived_by
    finding.waived_reason = item.waived_reason


def print_summary(karte, path, issue, round_no, accepted, outcome) -> None:
    created, resolved, excluded = outcome
    print(f"=== ingest-review: issue-{issue} round {round_no} ===")
    print(f"  取り込み: {len(accepted)} 件（新規 {len(created)} / 再掲 {len(accepted) - len(created)}）")
    if created:
        print(f"  新規採番: {', '.join(created)}")
    if resolved:
        print(f"  解消（レポートで `status: resolved` と明示された）: {', '.join(sorted(resolved))}")
    if excluded:
        print(f"  重複判定の明示的除外（distinct_from）: {'; '.join(excluded)}")
    print(f"  未解消: {', '.join(sorted(ingest_checks.open_ids(karte))) or '(なし)'}")
    out_of_scope = sorted(item.id for item in karte.open_findings() if item.scope == "out")
    if out_of_scope:
        # Issue #495: スコープ外の申告も同じ列に入ったことを取り込み時点で見せる。
        print(f"  うち scope: out（実害判定・verdict の免除にはならない）: {', '.join(out_of_scope)}")
    undecided = sorted(item.id for item in karte.undecided_findings())
    if undecided:
        print(
            "  実害あり・disposition 未決定（clean を妨げる。fix-here / deferred / waived を決める）: "
            + ", ".join(undecided)
        )
    print(f"  カルテ: {path}")
