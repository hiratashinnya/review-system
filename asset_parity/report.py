"""Builds the presence/absence matrix (+ staleness flags) and renders it.

Primary output: an asset × tree presence matrix (the thing that would have caught the
`issue-pipeline`-missing-from-two-trees case an earlier manual audit found). Secondary,
informational-only output: a lightweight staleness flag for pairs present in both the
canonical tree and a mirror, and a list of assets that exist in a mirror tree but have
no canonical `.claude/` counterpart at all (the reverse-direction gap).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from . import staleness as staleness_mod
from .exceptions import is_exempt
from .inventory import Asset, scan_canonical
from .trees import ALL_TREES, TREE_LABELS, applicable_trees, expected_paths, mirror_root_dirs

STATUS_PRESENT = "present"
STATUS_MISSING = "missing"
STATUS_EXEMPT = "exempt"
STATUS_NA = "na"


@dataclasses.dataclass(frozen=True)
class Cell:
    status: str
    path: Path | None = None
    reason: str | None = None
    stale: "staleness_mod.StaleSignal | None" = None


@dataclasses.dataclass(frozen=True)
class AssetRow:
    asset: Asset
    cells: dict[str, Cell]


@dataclasses.dataclass(frozen=True)
class Report:
    rows: list[AssetRow]
    orphans: dict[str, list[str]]  # tree -> sorted asset names present only in the mirror

    @property
    def missing_count(self) -> int:
        return sum(1 for row in self.rows for cell in row.cells.values()
                   if cell.status == STATUS_MISSING)

    @property
    def stale_flag_count(self) -> int:
        return sum(1 for row in self.rows for cell in row.cells.values()
                   if cell.stale is not None and cell.stale.flagged)


def build_report(
    root: Path,
    *,
    day_threshold: int = staleness_mod.DEFAULT_DAY_THRESHOLD,
    size_ratio_threshold: float = staleness_mod.DEFAULT_SIZE_RATIO_THRESHOLD,
    commit_epoch_fn=staleness_mod.git_last_commit_epoch,
    is_exempt_fn=is_exempt,
) -> Report:
    assets = scan_canonical(root)
    rows: list[AssetRow] = []

    for asset in assets:
        cells: dict[str, Cell] = {}
        for tree in ALL_TREES:
            if tree not in applicable_trees(asset.kind):
                cells[tree] = Cell(status=STATUS_NA)
                continue

            candidates = expected_paths(asset, tree, root)
            if not candidates:
                cells[tree] = Cell(
                    status=STATUS_EXEMPT,
                    reason="structural: inlined per asset-lateral-deploy routing "
                           "(user-invocable: false has no discrete Copilot file)",
                )
                continue

            found = next((p for p in candidates if p.is_file()), None)
            if found is not None:
                stale = staleness_mod.compare(
                    asset.canonical_path, found, root,
                    day_threshold=day_threshold,
                    size_ratio_threshold=size_ratio_threshold,
                    commit_epoch_fn=commit_epoch_fn,
                )
                cells[tree] = Cell(status=STATUS_PRESENT, path=found, stale=stale)
                continue

            reason = is_exempt_fn(asset.name, asset.kind, tree)
            if reason is not None:
                cells[tree] = Cell(status=STATUS_EXEMPT, reason=reason)
            else:
                cells[tree] = Cell(status=STATUS_MISSING)

        rows.append(AssetRow(asset=asset, cells=cells))

    orphans = _find_orphans(root, assets)
    return Report(rows=rows, orphans=orphans)


def _find_orphans(root: Path, assets: list[Asset]) -> dict[str, list[str]]:
    """Assets that exist in a mirror tree but have no canonical `.claude/` counterpart."""
    canonical_names = {(a.kind, a.name) for a in assets}
    orphans: dict[str, list[str]] = {}

    for tree in ALL_TREES:
        for kind in ("skill", "agent"):
            for mirror_dir in mirror_root_dirs(tree, kind, root):
                if not mirror_dir.is_dir():
                    continue
                if kind == "skill":
                    names = {p.parent.name for p in mirror_dir.glob("*/SKILL.md")}
                    names |= {p.name.removesuffix(".prompt.md")
                             for p in mirror_dir.glob("*.prompt.md")}
                else:
                    names = {p.name.removesuffix(".agent.md")
                             for p in mirror_dir.glob("*.agent.md")}
                    names |= {p.stem for p in mirror_dir.glob("*.toml")}
                extra = sorted(n for n in names if (kind, n) not in canonical_names)
                if extra:
                    orphans.setdefault(tree, [])
                    for n in extra:
                        label = f"{n} ({kind})"
                        if label not in orphans[tree]:
                            orphans[tree].append(label)

    for tree in orphans:
        orphans[tree].sort()
    return orphans


def to_jsonable(report: Report) -> dict:
    def cell_json(cell: Cell) -> dict:
        d: dict = {"status": cell.status}
        if cell.path is not None:
            d["path"] = str(cell.path)
        if cell.reason is not None:
            d["reason"] = cell.reason
        if cell.stale is not None:
            s = cell.stale
            d["stale"] = {
                "flagged": s.flagged,
                "reasons": list(s.flag_reasons),
                "day_gap": s.day_gap,
                "canonical_lines": s.canonical_lines,
                "mirror_lines": s.mirror_lines,
                "size_ratio": s.size_ratio,
            }
        return d

    return {
        "assets": [
            {
                "name": row.asset.name,
                "kind": row.asset.kind,
                "mode": row.asset.mode,
                "canonical_path": str(row.asset.canonical_path),
                "trees": {tree: cell_json(cell) for tree, cell in row.cells.items()},
            }
            for row in report.rows
        ],
        "orphans": report.orphans,
        "summary": {
            "asset_count": len(report.rows),
            "missing_count": report.missing_count,
            "stale_flag_count": report.stale_flag_count,
        },
    }


def render_json(report: Report) -> str:
    return json.dumps(to_jsonable(report), ensure_ascii=False, indent=2, sort_keys=False)


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
        lines.append("Orphans in mirror trees (present in a mirror, no canonical .claude/ "
                     "counterpart — informational only, not counted above):")
        for tree in ALL_TREES:
            names = report.orphans.get(tree)
            if names:
                lines.append(f"  {TREE_LABELS[tree]}: {', '.join(names)}")

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
        (row.asset.name, tree, row.cells[tree].stale)
        for row in report.rows
        for tree in ALL_TREES
        if row.cells[tree].status == STATUS_PRESENT
        and row.cells[tree].stale is not None
        and row.cells[tree].stale.flagged
    ]
    if stale_details:
        lines.append("")
        lines.append("Staleness flags (heuristic, false positives OK — worth a human/LLM look):")
        for name, tree, stale in stale_details:
            for reason in stale.flag_reasons:
                lines.append(f"  {name} @ {TREE_LABELS[tree]}: {reason}")

    return "\n".join(lines) + "\n"
