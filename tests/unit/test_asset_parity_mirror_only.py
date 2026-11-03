"""Mirror-only classification preserves raw detection and exact keys."""
import unittest
from pathlib import Path

from asset_parity.report import build_report, to_jsonable, render_text
from asset_parity.trees import AGENTS_DIR, CODEX, GITHUB
from tests.unit.asset_parity_fixtures import make_tree


class TestMirrorOnly(unittest.TestCase):
    def test_detection_classification_and_removal(self):
        root = make_tree(self)
        paths = {
            GITHUB: root / '.github/agents/doc-system-v2-authoring.agent.md',
            CODEX: root / '.codex/agents/doc-system-v2-authoring.toml',
            AGENTS_DIR: root / '.agents/skills/doc-system-config/SKILL.md',
        }
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture', encoding='utf-8')
        unknown = root / '.codex/agents/doc-system-v2-authoring-extra.toml'
        unknown.write_text('fixture', encoding='utf-8')
        wrong_kind = root / '.github/skills/doc-system-v2-authoring/SKILL.md'
        wrong_kind.parent.mkdir(parents=True, exist_ok=True)
        wrong_kind.write_text('fixture', encoding='utf-8')
        wrong_tree = root / '.github/skills/doc-system-config/SKILL.md'
        wrong_tree.parent.mkdir(parents=True, exist_ok=True)
        wrong_tree.write_text('fixture', encoding='utf-8')

        def payload():
            return to_jsonable(build_report(root, commit_epoch_fn=lambda p, r: None))

        result = payload()
        self.assertEqual(sum(map(len, result['documented_mirror_only'].values())), 3)
        self.assertTrue(all(entry['reason'] for entries in result['documented_mirror_only'].values() for entry in entries))
        self.assertIn('doc-system-v2-authoring (agent)', result['orphans'][CODEX])
        self.assertIn('doc-system-v2-authoring-extra (agent)', result['unclassified_orphans'][CODEX])
        self.assertIn('doc-system-v2-authoring (skill)', result['unclassified_orphans'][GITHUB])
        self.assertIn('doc-system-config (skill)', result['unclassified_orphans'][GITHUB])
        for path in paths.values():
            path.unlink()
        result = payload()
        self.assertEqual(result['documented_mirror_only'], {})
        self.assertNotIn('doc-system-v2-authoring (agent)', result['orphans'].get(CODEX, []))

    def test_real_tree(self):
        report = build_report(Path(__file__).resolve().parents[2])
        result = to_jsonable(report)
        self.assertEqual(sum(map(len, result['documented_mirror_only'].values())), 3)
        self.assertEqual(result['unclassified_orphans'], {})
        self.assertIn('Unclassified orphans: 0', render_text(report))


if __name__ == '__main__':
    unittest.main()
