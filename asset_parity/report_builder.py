"""Build the presence matrix from seed assets and mirror candidates."""

from pathlib import Path

from . import staleness as staleness_mod
from .exceptions import is_exempt
from .inventory import scan_parity_seeds
from .report_model import (Cell, AssetRow, Report, STATUS_NA, STATUS_EXEMPT,
                           STATUS_PRESENT, STATUS_MISSING)
from .report_orphans import _find_orphans
from .trees import ALL_TREES, applicable_trees, expected_paths


def build_report(
    root: Path,
    *,
    day_threshold: int = staleness_mod.DEFAULT_DAY_THRESHOLD,
    size_ratio_threshold: float = staleness_mod.DEFAULT_SIZE_RATIO_THRESHOLD,
    commit_epoch_fn=staleness_mod.git_last_commit_epoch,
    is_exempt_fn=is_exempt,
) -> Report:
    assets = scan_parity_seeds(root)
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
                    asset.parity_seed_path, found, root,
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


