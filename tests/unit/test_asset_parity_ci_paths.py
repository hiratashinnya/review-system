"""Cross-checks `.github/workflows/asset-parity.yml`'s `paths:` trigger filter
against the tree/mirror-root definitions in `asset_parity/trees.py` and
`asset_parity/inventory.py` (Issue #467).

This is a "does the CI *trigger* match what the tool actually *scans*" drift
guard, not a test of `asset_parity`'s inspection logic itself (see the other
`test_asset_parity_*.py` modules for that). It exists because this exact
class of drift already shipped silently once: `asset_parity/trees.py`
(`mirror_root_dirs()`) already scanned `.github/prompts/` for the Copilot
orchestrator-skill mirror, and `.ai/**` was added as the common normative
Source of Truth (#448), but neither path was added to the workflow's
`paths:` filter — a PR touching only those paths would never trigger
`asset-parity` at all. Issue #467 fixed the filter; this test fails the
build again if the two drift apart in the future (e.g. `trees.py` grows a
new mirror root without the workflow being updated to match).

`.ai/**` is treated as a documented *trigger-only* exception (see
`TRIGGER_ONLY_PATHS` below and the comment block in `asset-parity.yml`
itself): it must trigger the workflow, but it does not correspond to a
scanned tree root, because `asset_parity`'s inventory boundary intentionally
excludes `.ai/` from `check`'s own inspection (Issue #407, unchanged by
#467 — trigger condition and inspection scope are separate axes).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from asset_parity.inventory import (
    AGENT,
    PARITY_SEED_AGENTS_DIR,
    PARITY_SEED_SKILLS_DIR,
    SKILL,
)
from asset_parity.trees import ALL_TREES, mirror_root_dirs

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "asset-parity.yml"

# Paths intentionally present in the workflow's `paths:` filter that do NOT
# correspond to a tree/mirror root scanned by asset_parity/{trees,inventory}.py.
# Each entry here MUST have a matching rationale comment in asset-parity.yml
# itself (Issue #467 review contract) — this set is the allowlist for the
# "extra trigger path that isn't a real inventory/mirror tree" side of the
# check below, so adding a new undocumented trigger path fails loudly instead
# of silently passing.
TRIGGER_ONLY_PATHS = {
    ".ai/**",  # Issue #407/#467: trigger-only; asset_parity inventory scope is unchanged
    "asset_parity/**",  # the tool's own implementation
    ".github/workflows/asset-parity.yml",  # the workflow file itself
}


def _extract_paths_blocks(text: str) -> dict[str, list[str]]:
    """Parse the `push:`/`pull_request:` `paths:` lists out of the workflow YAML.

    Deliberately minimal (no PyYAML dependency, matching this repo's
    stdlib-only discipline — see `asset_parity/frontmatter.py`'s docstring
    for the same rationale applied to a different file format): walks the
    `on:` block line by line, and under each `push:`/`pull_request:` key,
    collects quoted list items following a `paths:` key until the block
    dedents.
    """
    blocks: dict[str, list[str]] = {}
    current_trigger: str | None = None
    in_paths = False
    paths_indent = -1
    for line in text.splitlines():
        trigger_match = re.match(r"^  (push|pull_request):\s*$", line)
        if trigger_match:
            current_trigger = trigger_match.group(1)
            blocks[current_trigger] = []
            in_paths = False
            continue
        if current_trigger is None:
            continue
        paths_match = re.match(r"^(\s+)paths:\s*$", line)
        if paths_match:
            in_paths = True
            paths_indent = len(paths_match.group(1))
            continue
        if in_paths:
            item_match = re.match(r'^(\s+)-\s+"(.+)"\s*$', line)
            if item_match and len(item_match.group(1)) > paths_indent:
                blocks[current_trigger].append(item_match.group(2))
                continue
            in_paths = False
    return blocks


def _expected_tree_paths() -> set[str]:
    """Derive the glob paths that MUST be covered by the workflow's `paths:`.

    Union of: the two `.claude/` parity-seed roots (`inventory.py`) and every
    mirror root `asset_parity/trees.py::mirror_root_dirs()` actually scans,
    across both asset kinds and all three mirror trees. Reads the real
    functions rather than re-deriving the list by hand, so this test tracks
    `trees.py`/`inventory.py` automatically instead of needing a manual
    update whenever a new mirror root is added there.
    """
    root = Path(".")
    dirs = {PARITY_SEED_SKILLS_DIR, PARITY_SEED_AGENTS_DIR}
    for kind in (SKILL, AGENT):
        for tree in ALL_TREES:
            for directory in mirror_root_dirs(tree, kind, root):
                dirs.add(directory.relative_to(root).as_posix())
    return {f"{d}/**" for d in dirs}


class TestAssetParityCiPathsMatchTrees(unittest.TestCase):
    def setUp(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.blocks = _extract_paths_blocks(text)
        self.expected_tree_paths = _expected_tree_paths()

    def test_workflow_has_push_and_pull_request_paths(self) -> None:
        self.assertIn("push", self.blocks)
        self.assertIn("pull_request", self.blocks)
        self.assertTrue(self.blocks["push"], "push.paths parsed empty — parser or YAML drifted")
        self.assertTrue(
            self.blocks["pull_request"],
            "pull_request.paths parsed empty — parser or YAML drifted",
        )

    def test_push_and_pull_request_paths_are_identical(self) -> None:
        self.assertEqual(
            set(self.blocks["push"]),
            set(self.blocks["pull_request"]),
            "push.paths and pull_request.paths must stay identical",
        )

    def test_every_scanned_tree_root_is_covered_by_paths_filter(self) -> None:
        for trigger, configured in self.blocks.items():
            missing = self.expected_tree_paths - set(configured)
            self.assertFalse(
                missing,
                f"{trigger}.paths in asset-parity.yml is missing tree root(s) "
                f"that asset_parity/trees.py or inventory.py actually scans: "
                f"{sorted(missing)} — a PR touching only these paths would "
                f"silently not trigger asset-parity (this is the exact class "
                f"of drift Issue #467 fixed for .github/prompts/**).",
            )

    def test_no_undocumented_extra_paths(self) -> None:
        allowed = self.expected_tree_paths | TRIGGER_ONLY_PATHS
        for trigger, configured in self.blocks.items():
            extra = set(configured) - allowed
            self.assertFalse(
                extra,
                f"{trigger}.paths in asset-parity.yml has entries that are "
                f"neither a scanned tree root nor in this test's "
                f"TRIGGER_ONLY_PATHS allowlist: {sorted(extra)} — if this is "
                f"an intentional new trigger-only addition, add it to "
                f"TRIGGER_ONLY_PATHS here with a rationale, and add a "
                f"matching comment in asset-parity.yml (Issue #467 review "
                f"contract).",
            )

    def test_ai_dir_triggers_as_documented_exception(self) -> None:
        for trigger, configured in self.blocks.items():
            self.assertIn(
                ".ai/**",
                configured,
                f"{trigger}.paths should include '.ai/**' as a trigger-only "
                f"addition (Issue #467) even though asset_parity's own "
                f"inventory boundary excludes .ai/ from inspection (#407).",
            )


if __name__ == "__main__":
    unittest.main()
