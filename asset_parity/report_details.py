"""Format missing and stale matrix details."""

from .report_model import Report, STATUS_MISSING, STATUS_PRESENT
from .trees import ALL_TREES, TREE_LABELS


def render_details(report: Report) -> list[str]:
    lines: list[str] = []
    missing_details = [
        (row.asset.name, tree)
        for row in report.rows
        for tree in ALL_TREES
        if row.cells[tree].status == STATUS_MISSING
    ]
    if missing_details:
        lines.append("")
        lines.append("MISSING detail:")
        for name, tree in missing_details:
            lines.append(f"  {name}: missing from {TREE_LABELS[tree]}")

    stale_details = [
        (row.asset.name, tree, stale)
        for row in report.rows
        for tree in ALL_TREES
        if row.cells[tree].status == STATUS_PRESENT
        and (stale := row.cells[tree].stale) is not None
        and stale.flagged
    ]
    if stale_details:
        lines.append("")
        lines.append("Staleness flags (heuristic, false positives OK — worth a human/LLM look):")
        for name, tree, stale in stale_details:
            for reason in stale.flag_reasons:
                lines.append(f"  {name} @ {TREE_LABELS[tree]}: {reason}")

    misplaced = [
        (row.asset.name, tree, cell.reason)
        for row in report.rows for tree, cell in row.cells.items()
        if cell.reason and "misplaced files:" in cell.reason
    ]
    if misplaced:
        lines.extend(["", "Misplaced files (not accepted as mirrors):"])
        lines.extend(f"  {name} @ {TREE_LABELS[tree]}: {reason}"
                     for name, tree, reason in misplaced)
    return lines
