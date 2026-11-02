"""``ingest-review`` の標準出力の契約（``ingest_report.print_report``）。

出力は主文脈が読んで処置方針を決める唯一の取り込み結果なので、行の有無と文言を固定する。
Issue #495 の「実害あり・disposition 未決定」行と ``scope: out`` 行は、免除にならないことを見せる。
"""

import unittest

from karte import exit_codes
from tests.unit.karte_support import finding, make_tmp_repo, report_text, run_cli

HARMFUL = finding("a.py::f", "f が入力検査をしていない")
OUT_OF_SCOPE = finding("c.py::g", "g が戻り値を握りつぶしている", scope="out")
COSMETIC = finding("e.py::h", "h の表記がゆれている", harm="none", severity="minor")
UNDECIDED = "  実害あり・disposition 未決定（clean を妨げる。fix-here / deferred / waived を決める）: "
SCOPE_OUT = "  うち scope: out（実害判定・verdict の免除にはならない）: "


class TestIngestStdout(unittest.TestCase):
    def setUp(self):
        self.root = make_tmp_repo(self, "karte-rep-")
        self.ledger = self.root / "tmp" / "_karte" / "issue-7.md"

    def _ingest(self, round_no, *blocks):
        argv = ["ingest-review", "--issue", "7", "--round", str(round_no), "--from", "-"]
        code, out, err = run_cli(self.root, argv, report_text(*blocks))
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        self.assertEqual("", err)
        return out.splitlines()

    def test_first_round_lists_new_ids_scope_out_and_undecided_real_harm(self):
        lines = self._ingest(1, ("new", HARMFUL), ("new", OUT_OF_SCOPE), ("new", COSMETIC))
        self.assertEqual(
            [
                "=== ingest-review: issue-7 round 1 ===",
                "  取り込み: 3 件（新規 3 / 再掲 0）",
                "  新規採番: F-7-01, F-7-02, F-7-03",
                "  未解消: F-7-01, F-7-02, F-7-03",
                SCOPE_OUT + "F-7-02",
                UNDECIDED + "F-7-01, F-7-02",
                f"  カルテ: {self.ledger}",
            ],
            lines,
        )

    def test_later_round_reports_resolved_and_reposted_counts(self):
        self._ingest(1, ("new", HARMFUL), ("new", OUT_OF_SCOPE), ("new", COSMETIC))
        lines = self._ingest(
            2,
            ("F-7-01", {**HARMFUL, "status": "resolved"}),
            ("F-7-02", OUT_OF_SCOPE),
            ("F-7-03", COSMETIC),
        )
        self.assertEqual(
            [
                "=== ingest-review: issue-7 round 2 ===",
                "  取り込み: 3 件（新規 0 / 再掲 3）",
                "  解消（レポートで `status: resolved` と明示された）: F-7-01",
                "  未解消: F-7-02, F-7-03",
                SCOPE_OUT + "F-7-02",
                UNDECIDED + "F-7-02",
                f"  カルテ: {self.ledger}",
            ],
            lines,
        )

    def test_nothing_open_prints_no_open_scope_out_or_undecided_lines(self):
        self._ingest(1, ("new", HARMFUL))
        lines = self._ingest(2, ("F-7-01", {**HARMFUL, "status": "resolved"}))
        self.assertEqual(
            [
                "=== ingest-review: issue-7 round 2 ===",
                "  取り込み: 1 件（新規 0 / 再掲 1）",
                "  解消（レポートで `status: resolved` と明示された）: F-7-01",
                "  未解消: (なし)",
                f"  カルテ: {self.ledger}",
            ],
            lines,
        )

    def test_distinct_from_exclusion_is_shown(self):
        self._ingest(1, ("new", HARMFUL))
        lines = self._ingest(2, ("F-7-01", HARMFUL), ("new", {**HARMFUL, "distinct_from": "F-7-01"}))
        excluded = [line for line in lines if "distinct_from" in line]
        self.assertEqual(1, len(excluded), lines)
        self.assertTrue(excluded[0].startswith("  重複判定の明示的除外（distinct_from）: "), excluded)
        self.assertIn("F-7-01", excluded[0])


if __name__ == "__main__":
    unittest.main()
