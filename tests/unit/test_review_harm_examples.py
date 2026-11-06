"""Karte's harm, scope and disposition remain independent data fields."""
import unittest

from karte import model


def report(harm, scope, detail):
    return f'''### new
harm: {harm}
harm_detail: {detail}
severity: major
scope: {scope}
locus: file.py
summary: 判定例
evidence: 実体を確認
expected: 根拠に一致
recheck: 再確認
'''


class ReviewHarmExamples(unittest.TestCase):
    def test_harm_and_scope_are_independent_in_all_four_combinations(self):
        examples = [('real', 'in', '入力が消えてデータが失われる'),
                    ('real', 'out', '権限検査を迂回できる'),
                    ('none', 'in', '語順の好みで挙動は変わらない'),
                    ('none', 'out', '整形の好みで挙動は変わらない')]
        for harm, scope, detail in examples:
            with self.subTest(harm=harm, scope=scope):
                finding, = model.parse_review(report(harm, scope, detail), 723)
                self.assertEqual((finding.harm, finding.scope, finding.harm_detail),
                                 (harm, scope, detail))
                self.assertEqual(finding.disposition, '')
                recorded = model.Finding(id="F-723-01", harm=harm, scope=scope,
                                         harm_detail=detail)
                self.assertTrue(recorded.needs_remediation)

    def test_disposition_history_is_rejected_as_harm_detail(self):
        for detail in ('対応不要と判断した', 'オーナー確認済み', '別 Issue で直すべき'):
            with self.subTest(detail=detail), self.assertRaises(model.KarteFormatError):
                model.parse_review(report('real', 'out', detail), 723)


if __name__ == '__main__':
    unittest.main()
