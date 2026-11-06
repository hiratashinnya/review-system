"""Independent baseline for the historical harm contract, not a classifier."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = '.ai/skills/review-harm/SKILL.md'
# Captured from main's issue-pipeline before extraction; each clause is material.
ORIGINAL = (
    '仕様・設計との不一致、テスト退行、期待値の誤り',
    'fail-close、機械ゲート、検証、権限境界の迂回',
    '正本・履歴・データの破損、契約違反、秘密・無認可コスト',
    '後工程の誤読、名前と実体の不一致、トレーサビリティ断絶、正本の分岐、暗黙の前提、観測不能、再現性の欠如',
)


def copied_definition(text):
    """Detect a copied enumeration even when punctuation or line wrapping changes."""
    signatures = ('fail-close', 'トレーサビリティ断絶', '正本の分岐',
                  '暗黙の前提', '観測不能', '再現性の欠如')
    return sum(word in text for word in signatures) >= 4


class NormativeTests(unittest.TestCase):
    def test_original_detail_is_preserved_and_assigned_to_real(self):
        text = (ROOT / SOURCE).read_text(encoding='utf-8')
        real = text.index('real')
        for clause in ORIGINAL:
            with self.subTest(clause=clause):
                self.assertGreater(text.index(clause), real)
        for boundary in ('語順', '整形', '根拠のない推測', 'none', '迷',
                         'scope: out', 'harm_detail', '処置方針', 'オーナー'):
            self.assertIn(boundary, text)

    def test_four_examples_are_declared_with_independent_expectations(self):
        text = (ROOT / SOURCE).read_text(encoding='utf-8')
        # Each row gives an example and harm/scope independently, not a computed classifier.
        cases = (('real', 'in', 'データ'), ('real', 'out', '権限'),
                 ('none', 'in', '語順'), ('none', 'out', '整形'))
        for harm, scope, example in cases:
            with self.subTest(harm=harm, scope=scope):
                rows = [line for line in text.splitlines()
                        if re.search(rf'\b{harm}\b', line) and re.search(rf'\b{scope}\b', line)
                        and example in line]
                self.assertTrue(any(len(row) > 30 for row in rows))

    def test_consumers_have_no_copied_definition(self):
        paths = ('.ai/agents/pr-reviewer.md', '.ai/agents/plan-reviewer.md',
                 '.ai/skills/issue-pipeline/SKILL.md')
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(copied_definition((ROOT / path).read_text(encoding='utf-8')))
        self.assertTrue(copied_definition(' '.join(ORIGINAL)))

    def test_reference_and_mandatory_read_are_in_same_instruction(self):
        for path in ('.ai/agents/pr-reviewer.md', '.ai/agents/plan-reviewer.md',
                     '.ai/skills/issue-pipeline/SKILL.md'):
            body = (ROOT / path).read_text(encoding='utf-8')
            lines = [line for line in body.splitlines() if SOURCE in line]
            with self.subTest(path=path):
                self.assertTrue(any('必ず' in line and ('読む' in line or '読' in line)
                                    for line in lines))
                self.assertTrue((ROOT / SOURCE).is_file())


if __name__ == '__main__':
    unittest.main()
