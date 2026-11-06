"""Find mirror assets without a Claude parity seed."""

from pathlib import Path

from .exceptions import mirror_only_reason
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
                    names = {p.parent.name for p in mirror_dir.glob("*/SKILL.md") if p.is_file()}
                    names |= {p.name.removesuffix(".prompt.md")
                             for p in mirror_dir.glob("*.prompt.md") if p.is_file()}
                else:
                    names = {p.name.removesuffix(".agent.md")
                             for p in mirror_dir.glob("*.agent.md") if p.is_file()}
                    names |= {p.stem for p in mirror_dir.glob("*.toml") if p.is_file()}
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



def classify_orphans(orphans: dict[str, list[str]]) -> tuple[dict, dict]:
    """Classify only detected orphans, retaining raw labels and their tree."""
    documented: dict[str, list[dict[str, str]]] = {}
    unclassified: dict[str, list[str]] = {}
    for tree, labels in orphans.items():
        for label in labels:
            name, sep, kind = label.rpartition(" (")
            reason = mirror_only_reason(name, kind[:-1], tree) if sep and kind.endswith(")") else None
            if reason is None:
                unclassified.setdefault(tree, []).append(label)
            else:
                documented.setdefault(tree, []).append({"name": name, "kind": kind[:-1], "reason": reason})
    return documented, unclassified
