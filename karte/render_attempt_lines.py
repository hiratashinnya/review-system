from __future__ import annotations

from . import model


def render_attempt_lines(karte: model.Karte) -> list[str]:
    """過去の試行と結果を整形する。"""
    lines: list[str] = []
    lines.append("## Prior attempts（DO NOT repeat these）")
    if not karte.attempts:
        lines.append("  (まだ試行なし)")
    for attempt in karte.attempts:
        measured = karte.touched_of(attempt.number)
        lines.append(
            f"  - Attempt {attempt.number} [round {attempt.round}] "
            f"root_cause={attempt.root_cause} change_kind={attempt.change_kind}"
        )
        lines.append(f"      finding_ids: {', '.join(attempt.finding_ids)}")
        lines.append(f"      targets: {', '.join(attempt.targets)}")
        if attempt.diagnosis:
            lines.append(f"      diagnosis: {attempt.diagnosis}")
        if measured:
            lines.append(f"      実測 touched: {', '.join(measured)}")
        for result in karte.results_for(attempt.number):
            note = f" / {result.note}" if result.note else ""
            lines.append(f"      → Result: {result.outcome}{note}")
        if not karte.results_for(attempt.number):
            lines.append("      → Result: (未クローズ。修正後に `close-attempt` で実測を記録する)")

    return lines
