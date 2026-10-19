"""Public asset inventory API and parity seed path boundaries."""

from pathlib import Path

from .asset import Asset
from .seed_scan import scan_parity_seeds
from .seed_paths import (AGENT, SKILL, MODE_SKILL, MODE_ORCHESTRATOR, MODE_PRINCIPLE,
                         COMMON_SOT_SKILLS_DIR, COMMON_SOT_AGENTS_DIR,
                         NON_NORMATIVE_SHARED_DIRS, PARITY_SEED_SKILLS_DIR,
                         PARITY_SEED_AGENTS_DIR)


def is_parity_seed_path(path: Path | str, root: Path) -> bool:
    """Return whether ``path`` is in one of the two parity seed roots.

    This is intentionally a path-boundary helper rather than a recursive
    ``.claude`` check.  Rationale/troubleshooting/schema files are repository
    records and must never be promoted to parity assets merely because they
    happen to be Markdown files.
    """

    try:
        path_obj = Path(path)
        candidate = path_obj if path_obj.is_absolute() else root / path_obj
        relative = candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    parts = relative.parts
    if len(parts) < 3:
        return False
    if parts[:2] == tuple(PARITY_SEED_SKILLS_DIR.split("/")):
        return parts[-1] == "SKILL.md" and len(parts) == 4
    if parts[:2] == tuple(PARITY_SEED_AGENTS_DIR.split("/")):
        return parts[-1].endswith(".md") and len(parts) == 3
    return False


def scan_canonical(root: Path) -> list[Asset]:
    """Deprecated compatibility alias for :func:`scan_parity_seeds`."""
    return scan_parity_seeds(root)


def is_canonical_asset_path(path: Path | str, root: Path) -> bool:
    """Deprecated compatibility alias for :func:`is_parity_seed_path`."""
    return is_parity_seed_path(path, root)
