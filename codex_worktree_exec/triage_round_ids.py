"""Resolve the exact finding IDs committed by the normal Karte ingestion."""

from karte import karte_loader
from karte.review_report import parse_review


def ingested_finding_ids(body: bytes, main_root, issue: int, round_no: int) -> list[str]:
    """Attest IDs from the ingested Karte, never manufacture a temporary ID."""
    report = parse_review(body.decode("utf-8"), issue)
    _path, karte = karte_loader.load_karte(main_root, issue)
    explicit = {finding.finding_id for finding in report if finding.finding_id is not None}
    created = sorted(
        (finding for finding in karte.findings
         if round_no in finding.rounds and min(finding.rounds) == round_no
         and finding.id not in explicit),
        key=lambda finding: finding.seq,
    )
    if len(created) != sum(finding.finding_id is None for finding in report):
        raise ValueError("ingested new finding count differs from reviewer output")
    fresh = iter(created)
    result = []
    for item in report:
        assigned = karte.finding(item.finding_id) if item.finding_id else next(fresh)
        if assigned is None or round_no not in assigned.rounds:
            raise ValueError("review finding was not ingested in the expected round")
        for field in ("harm", "harm_detail", "severity", "status", "summary",
                      "evidence", "expected", "recheck", "locus"):
            original = getattr(item, field)
            observed = getattr(assigned, field)
            if field == "locus":
                original = list(original)
            if original != observed:
                raise ValueError("ingested finding content differs from reviewer output: " + field)
        result.append(assigned.id)
    if len(set(result)) != len(result):
        raise ValueError("duplicate ingested finding ID")
    return result
