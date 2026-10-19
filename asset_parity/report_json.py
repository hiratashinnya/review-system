"""JSON report serialization with deprecated key aliases."""

import json

from .report_model import Cell, Report


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
                "parity_seed_lines": s.parity_seed_lines,
                "canonical_lines": s.parity_seed_lines,
                "mirror_lines": s.mirror_lines,
                "size_ratio": s.size_ratio,
            }
        return d

    return {
        "schema": "asset-parity-report/v2",
        "compatibility": {
            "deprecated_keys": {
                "canonical_path": "parity_seed_path",
                "canonical_lines": "parity_seed_lines",
            },
        },
        "assets": [
            {
                "name": row.asset.name,
                "kind": row.asset.kind,
                "mode": row.asset.mode,
                "parity_seed_path": str(row.asset.parity_seed_path),
                "canonical_path": str(row.asset.parity_seed_path),
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


