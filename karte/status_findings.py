from __future__ import annotations

from . import model


def finding_rows(karte: model.Karte) -> list:
    """finding と関連する試行の機械可読行を作る。"""
    findings = []
    for finding in karte.findings:
        related = karte.attempts_for_finding(finding.id)
        findings.append(
            {
                "id": finding.id,
                "status": finding.status,
                "harm": finding.harm,
                "harm_detail": finding.harm_detail,
                "severity": finding.severity,
                "scope": finding.scope,
                "disposition": finding.disposition,
                "deferred_to": finding.deferred_to,
                "waived_by": finding.waived_by,
                "waived_reason": finding.waived_reason,
                "locus": list(finding.locus),
                "summary": finding.summary,
                "evidence": finding.evidence,
                "expected": finding.expected,
                "recheck": finding.recheck,
                "rounds": list(finding.rounds),
                "resolved_round": finding.resolved_round,
                "attempts": [
                    {
                        "attempt": item.number,
                        "round": item.round,
                        "root_cause": item.root_cause,
                        "change_kind": item.change_kind,
                        "targets": list(item.targets),
                        "results": [
                            {
                                "outcome": result.outcome,
                                "touched": list(result.touched),
                                "note": result.note,
                            }
                            for result in karte.results_for(item.number)
                        ],
                    }
                    for item in related
                ],
            }
        )
    return findings
