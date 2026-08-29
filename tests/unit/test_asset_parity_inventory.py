"""asset_parity.inventory — loader-facing parity seed棚卸しの契約。"""

import unittest

from asset_parity.inventory import AGENT, MODE_ORCHESTRATOR, MODE_PRINCIPLE, MODE_SKILL, SKILL, scan_canonical, scan_parity_seeds

from tests.unit.asset_parity_fixtures import make_tree


class TestScanParitySeeds(unittest.TestCase):
    def setUp(self):
        self.root = make_tree(self)
        self.assets = scan_parity_seeds(self.root)
        self.by_name = {(a.kind, a.name): a for a in self.assets}

    def test_finds_all_real_assets(self):
        names = {(a.kind, a.name) for a in self.assets}
        self.assertIn((SKILL, "plain-skill"), names)
        self.assertIn((AGENT, "plain-agent"), names)

    def test_skips_files_without_frontmatter(self):
        names = {(a.kind, a.name) for a in self.assets}
        self.assertNotIn((AGENT, "no-frontmatter"), names)

    def test_default_mode_is_skill(self):
        asset = self.by_name[(SKILL, "plain-skill")]
        self.assertEqual(asset.mode, MODE_SKILL)

    def test_disable_model_invocation_is_orchestrator_mode(self):
        asset = self.by_name[(SKILL, "orchestrator-skill")]
        self.assertEqual(asset.mode, MODE_ORCHESTRATOR)

    def test_user_invocable_false_is_principle_mode(self):
        asset = self.by_name[(SKILL, "principle-skill")]
        self.assertEqual(asset.mode, MODE_PRINCIPLE)

    def test_agent_mode_is_none(self):
        asset = self.by_name[(AGENT, "plain-agent")]
        self.assertIsNone(asset.mode)

    def test_parity_seed_path_points_at_real_file(self):
        asset = self.by_name[(SKILL, "plain-skill")]
        self.assertTrue(asset.parity_seed_path.is_file())
        self.assertEqual(asset.parity_seed_path.name, "SKILL.md")

    def test_deprecated_canonical_api_remains_compatible(self):
        legacy_assets = scan_canonical(self.root)
        self.assertEqual(legacy_assets, self.assets)
        asset = self.by_name[(SKILL, "plain-skill")]
        self.assertEqual(asset.canonical_path, asset.parity_seed_path)


if __name__ == "__main__":
    unittest.main()
