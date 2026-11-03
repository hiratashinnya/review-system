"""Mutation tests for generated harm criteria and its tracked consumption paths."""
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('.ai/skills/review-harm/SKILL.md')
TARGET = Path('.claude/skills/review-harm/SKILL.md')


class HarmSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for path in (SOURCE, TARGET):
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / path, self.root / path)

    def test_source_and_generated_file_mutations_each_fail_then_render_recovers(self):
        from review_harm_sync import check, render
        self.assertEqual(check(self.root), [])
        for path in (SOURCE, TARGET):
            with self.subTest(path=path):
                with (self.root / path).open('a', encoding='utf-8') as stream:
                    stream.write('\nchanged\n')
                self.assertTrue(check(self.root))
                render(self.root)
                self.assertEqual(check(self.root), [])

    def test_missing_generated_copy_is_detected_and_restored(self):
        from review_harm_sync import check, render
        (self.root / TARGET).unlink()
        self.assertTrue(check(self.root))
        render(self.root)
        self.assertEqual(check(self.root), [])

    def test_pipeline_wrappers_load_common_pipeline(self):
        common = '.ai/skills/issue-pipeline/SKILL.md'
        for path in ('.claude/skills/issue-pipeline/SKILL.md',
                     '.github/skills/issue-pipeline/SKILL.md'):
            with self.subTest(path=path):
                body = (ROOT / path).read_text(encoding='utf-8')
                self.assertIn(common, body)
                self.assertIn('必ず', body)

    def test_no_handwritten_thirteen_category_enumeration_in_consumers(self):
        signature = ('トレーサビリティ断絶', '暗黙の前提', '再現性の欠如')
        for path in ('.ai/agents/pr-reviewer.md', '.ai/agents/plan-reviewer.md',
                     '.ai/skills/issue-pipeline/SKILL.md'):
            body = (ROOT / path).read_text(encoding='utf-8')
            self.assertFalse(all(term in body for term in signature), path)


if __name__ == '__main__':
    unittest.main()
