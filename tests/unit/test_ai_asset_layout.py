"""Issue #407 の AI 資産配置・非活性境界の機械検査。"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from asset_parity.inventory import (
    CANONICAL_AGENTS_DIR,
    CANONICAL_SKILLS_DIR,
    NON_NORMATIVE_SHARED_DIRS,
    is_canonical_asset_path,
    scan_canonical,
)
from guidance_sync import NON_GUIDANCE_SHARED_DIRS, TARGETS


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / ".ai/schema/asset-placement-v1.json"
SHARED_DIRS = tuple(REPO_ROOT / relative for relative in NON_NORMATIVE_SHARED_DIRS)


class AiAssetPlacementContractTests(unittest.TestCase):
    def test_shared_schema_is_valid_json_and_declares_the_closed_contract(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["$id"].rsplit("/", 1)[-1], "asset-placement-v1.json")
        self.assertEqual(schema["type"], "object")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema"]["const"], "ai-asset-placement/v1")
        self.assertEqual(
            set(schema["$defs"]["entry"]["properties"]["category"]["enum"]),
            {"normative", "rationale", "troubleshooting", "shared-schema"},
        )

    def test_non_normative_directories_exist_and_are_documented(self):
        ai_readme = (REPO_ROOT / ".ai/README.md").read_text(encoding="utf-8")
        for relative, marker in (
            (".ai/rationale", "ADR／設計経緯"),
            (".ai/troubleshooting", "障害・復旧記録"),
            (".ai/schema", "共通 schema"),
        ):
            with self.subTest(relative=relative):
                self.assertTrue((REPO_ROOT / relative).is_dir())
                self.assertIn(relative, ai_readme)
                self.assertIn(marker, ai_readme)

    def test_inventory_has_only_loader_facing_canonical_roots(self):
        assets = scan_canonical(REPO_ROOT)
        self.assertTrue(assets)
        self.assertTrue(all(is_canonical_asset_path(asset.canonical_path, REPO_ROOT)
                            for asset in assets))
        self.assertTrue(all(
            str(asset.canonical_path).startswith(
                str(REPO_ROOT / CANONICAL_SKILLS_DIR)
            ) or str(asset.canonical_path).startswith(
                str(REPO_ROOT / CANONICAL_AGENTS_DIR)
            )
            for asset in assets
        ))
        self.assertTrue(is_canonical_asset_path(
            ".claude/skills/example/SKILL.md", REPO_ROOT
        ))
        self.assertFalse(is_canonical_asset_path(
            ".ai/rationale/example.md", REPO_ROOT
        ))

    def test_non_normative_records_cannot_be_canonical_assets(self):
        for directory in SHARED_DIRS:
            with self.subTest(directory=directory):
                self.assertTrue(directory.is_dir())
                for path in directory.rglob("*"):
                    if path.is_file():
                        self.assertFalse(is_canonical_asset_path(path, REPO_ROOT))

    def test_guidance_sync_does_not_load_non_normative_records(self):
        self.assertEqual(set(TARGETS), {"AGENTS.md", ".github/copilot-instructions.md"})
        self.assertTrue(all(
            not any(source.startswith(directory) for directory in NON_GUIDANCE_SHARED_DIRS)
            for source in TARGETS.values()
        ))

    def test_schema_path_patterns_are_specific_to_each_category(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        conditions = schema["$defs"]["entry"]["allOf"]
        examples = {
            "normative": ".ai/skills/example/SKILL.md",
            "rationale": ".ai/rationale/example.md",
            "troubleshooting": ".ai/troubleshooting/issue-pipeline.md",
            "shared-schema": ".ai/schema/asset-placement-v1.json",
        }
        for condition in conditions:
            category = condition["if"]["properties"]["category"]["const"]
            pattern = condition["then"]["properties"]["path"]["pattern"]
            with self.subTest(category=category):
                self.assertIsNotNone(re.fullmatch(pattern, examples[category]))
                self.assertIsNone(re.fullmatch(pattern, ".claude/rationale/example.md"))

    def test_troubleshooting_filename_contract_rejects_incident_suffixes(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        conditions = schema["$defs"]["entry"]["allOf"]
        troubleshooting = next(
            condition
            for condition in conditions
            if condition["if"]["properties"]["category"]["const"] == "troubleshooting"
        )
        pattern = troubleshooting["then"]["properties"]["path"]["pattern"]
        paths = sorted(
            path
            for path in (REPO_ROOT / ".ai/troubleshooting").glob("*.md")
            if path.name != "README.md"
        )
        self.assertTrue(paths)
        self.assertTrue(all(re.fullmatch(pattern, f".ai/troubleshooting/{path.name}") for path in paths))
        self.assertIsNone(re.fullmatch(pattern, ".ai/troubleshooting/issue-pipeline-runtime.md"))

    def test_tailoring_registry_records_the_placement_authority(self):
        registry = (REPO_ROOT / ".claude/tailoring-registry.md").read_text(encoding="utf-8")
        for marker in (
            ".ai/rationale/",
            ".ai/troubleshooting/",
            ".ai/schema/",
            ".ai/schema/asset-placement-v1.json",
            "asset_parity/inventory.py",
        ):
            self.assertIn(marker, registry)


if __name__ == "__main__":
    unittest.main()
