"""検証を通ったレビュー指摘を台帳の finding へ反映する。

設計理由は [.ai/rationale/karte-module-split.md](../.ai/rationale/karte-module-split.md)。
"""

from . import model
from .ingest_types import IngestOutcome


def apply_accepted(karte, accepted, round_no) -> IngestOutcome:
    created, resolved, excluded = [], [], []
    for entry in accepted:
        finding_id, item = entry.finding_id, entry.item
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
    return IngestOutcome(created, resolved, excluded)


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
