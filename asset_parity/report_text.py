"""Human-readable matrix presentation."""

from .report_model import (Report, STATUS_PRESENT, STATUS_MISSING, STATUS_EXEMPT, STATUS_NA)
from .report_details import render_details
from .report_orphans import classify_orphans
from .trees import ALL_TREES, TREE_LABELS


_STATUS_SYMBOL = {
    STATUS_PRESENT: "OK",
    STATUS_MISSING: "MISSING",
    STATUS_EXEMPT: "exempt",
    STATUS_NA: "n/a",
}


def render_text(report: Report) -> str:
    lines: list[str] = []
    lines.append("asset_parity — cross-platform asset presence matrix")
    lines.append("")
    header = f"{'asset':<28} {'kind':<6} {'mode':<12}" + "".join(
        f" {TREE_LABELS[t]:<28}" for t in ALL_TREES
    )
    lines.append(header)
    lines.append("-" * len(header))

    for row in report.rows:
        cell_strs = []
        for tree in ALL_TREES:
            cell = row.cells[tree]
            sym = _STATUS_SYMBOL[cell.status]
            if cell.status == STATUS_PRESENT and cell.stale is not None and cell.stale.flagged:
                sym += " [STALE?]"
            cell_strs.append(f"{sym:<28}")
        mode = row.asset.mode or "-"
        lines.append(f"{row.asset.name:<28} {row.asset.kind:<6} {mode:<12} " + " ".join(cell_strs))

    lines.append("")
    lines.append(f"{len(report.rows)} assets checked; "
                 f"{report.missing_count} MISSING; {report.stale_flag_count} staleness flag(s)")

    if report.orphans:
        lines.append("")
        lines.append("Orphans in mirror trees (present in a mirror, no .claude/ parity-seed "
                     "counterpart — informational only, not counted above):")
        for tree in ALL_TREES:
            names = report.orphans.get(tree)
            if names:
                lines.append(f"  {TREE_LABELS[tree]}: {', '.join(names)}")

    documented, unclassified = classify_orphans(report.orphans)
    lines.append("")
    lines.append(f"Documented mirror-only: {sum(map(len, documented.values()))}")
    for tree, entries in documented.items():
        for entry in entries:
            lines.append(f"  {TREE_LABELS[tree]}: {entry['name']} ({entry['kind']}) — {entry['reason']}")
    lines.append(f"Unclassified orphans: {sum(map(len, unclassified.values()))}")
    for tree, labels in unclassified.items():
        lines.append(f"  {TREE_LABELS[tree]}: {', '.join(labels)}")

    lines.extend(render_details(report))

    return "\n".join(lines) + "\n"
