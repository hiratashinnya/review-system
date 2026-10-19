"""Find mirror assets without a Claude parity seed."""

from pathlib import Path

from .inventory import Asset
from .trees import ALL_TREES, mirror_root_dirs


def _find_orphans(root: Path, assets: list[Asset]) -> dict[str, list[str]]:
    """Assets that exist in a mirror tree but have no `.claude/` parity seed."""
    seed_names = {(a.kind, a.name) for a in assets}
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
                extra = sorted(n for n in names if (kind, n) not in seed_names)
                if extra:
                    orphans.setdefault(tree, [])
                    for n in extra:
                        label = f"{n} ({kind})"
                        if label not in orphans[tree]:
                            orphans[tree].append(label)

    for tree in orphans:
        orphans[tree].sort()
    return orphans


