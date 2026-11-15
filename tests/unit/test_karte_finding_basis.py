"""Issue #830: finding 根拠欄の互換入力・保持・欠損/不正値を実経路で検査する。"""

from dataclasses import asdict
import unittest

from karte import model
from tests.unit.karte_support import RootedCase, finding, report_text


class FindingBasisTests(RootedCase):
    def _block(self, **overrides):
        return ("new", finding("a.py::f", "根拠欄のテスト", **overrides))

    def test_four_representative_findings_are_preserved(self):
        # PR #733 F-733-01 (CI head/merge identity) と #818 F-655-D03
        # (TOCTOU) の既存指摘を下敷きに、2欄は本テスト用に補った。
        cases = [
            ("理論上のみ", "根拠なし", "理論モデル上の仮想環境だけ"),
            ("悪意前提", "外部者が隔離済みの内部ファイルを直接変更", "悪意ある操作・境界越えは未実証"),
            ("うっかりで到達", "PR CIのmerge SHAをHEADとして読み違える", "通常のCI操作・悪意なし"),
            ("根拠欠落", "根拠なし", "根拠なし"),
            ("TOCTOU", "列挙後のunlink前に通常ファイルへ置換", "同時実行・誤消去、悪意不問"),
        ]
        for label, route, threat in cases:
            with self.subTest(label=label):
                item, = model.parse_review(
                    report_text(self._block(reachability_path=route, threat_assumption=threat)), 7
                )
                self.assertEqual((route, threat), (item.reachability_path, item.threat_assumption))
                self.assertEqual("real", item.harm)
                self.assertIn("reachability_path", asdict(item))
                self.assertIn("threat_assumption", asdict(item))

    def test_missing_legacy_fields_and_present_invalid_fields(self):
        legacy, = model.parse_review(report_text(self._block()), 7)
        self.assertEqual(("", ""), (legacy.reachability_path, legacy.threat_assumption))
        for key in ("reachability_path", "threat_assumption"):
            for invalid in ("", "   ", "[x, y]", "[]"):
                with self.subTest(key=key, invalid=invalid):
                    with self.assertRaises(model.KarteFormatError):
                        model.parse_review(report_text(self._block(**{key: invalid})), 7)

    def test_ingest_render_parse_and_old_round_do_not_discard_basis(self):
        route = "PR head とCI merge ref の対応規則に到達"
        threat = "通常のCI実行・悪意なし"
        code, _, err = self.ingest(
            1, self._block(reachability_path=route, threat_assumption=threat)
        )
        self.assertEqual(0, code, err)
        first = self.ledger().finding("F-7-01")
        self.assertEqual((route, threat), (first.reachability_path, first.threat_assumption))
        self.assertTrue(first.needs_disposition)
        old = ("F-7-01", self._block()[1])
        code, _, err = self.ingest(2, old)
        self.assertEqual(0, code, err)
        stored = self.ledger()
        item = stored.finding("F-7-01")
        self.assertEqual((route, threat), (item.reachability_path, item.threat_assumption))
        self.assertEqual((route, threat), (
            model.parse(model.dumps(stored)).finding("F-7-01").reachability_path,
            model.parse(model.dumps(stored)).finding("F-7-01").threat_assumption,
        ))
        code, _, err = self.ingest(3, ("F-7-01", self._block(
            reachability_path="根拠なし", threat_assumption="根拠なし"
        )[1]))
        self.assertEqual(0, code, err)
        item = self.ledger().finding("F-7-01")
        self.assertEqual(("根拠なし", "根拠なし"),
                         (item.reachability_path, item.threat_assumption))
        self.assertTrue(item.needs_disposition)

    def test_old_ledger_format_still_loads(self):
        self.assertEqual(0, self.ingest(1, self._block())[0])
        serialized = model.dumps(self.ledger())
        legacy = "".join(line for line in serialized.splitlines(keepends=True)
                         if not line.startswith(("reachability_path:", "threat_assumption:")))
        item = model.parse(legacy).finding("F-7-01")
        self.assertEqual(("", ""), (item.reachability_path, item.threat_assumption))
        self.assertEqual(model.parse(legacy).findings[0].harm, "real")


if __name__ == "__main__":
    unittest.main()
