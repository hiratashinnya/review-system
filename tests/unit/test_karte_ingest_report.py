"""``ingest-review`` の標準出力の契約（``ingest_report.print_report``）。

出力は主文脈が読んで処置方針を決める唯一の取り込み結果なので、行の有無と文言と並びを固定する。
Issue #495 の「実害あり・disposition 未決定」行と ``scope: out`` 行は、免除にならないことを見せる。
ID の並びは ``set`` の反復順に依存させない：件数を多くして、整列を外すと必ず崩れる入力にする。
"""

import unittest

from karte import exit_codes
from tests.unit.karte_support import RootedCase, finding

HARMFUL = finding("a.py::f", "f が入力検査をしていない")
OUT_OF_SCOPE = finding("c.py::g", "g が戻り値を握りつぶしている", scope="out")
COSMETIC = finding("e.py::h", "h の表記がゆれている", harm="none", severity="minor")
UNDECIDED = "  実害あり・disposition 未決定（clean を妨げる。fix-here / deferred / waived を決める）: "
SCOPE_OUT = "  うち scope: out（実害判定・verdict の免除にはならない）: "
DISTINCT = "  重複判定の明示的除外（distinct_from）: "
RESOLVED = "  解消（レポートで `status: resolved` と明示された）: "

MANY = 12  # 2 桁の連番が複数並ぶ件数（set の反復順と ID 順が一致する見込みをなくす）


def ids(*numbers) -> str:
    return ", ".join(f"F-7-{number:02d}" for number in numbers)


def distinct_finding(number, **overrides) -> dict:
    """互いに locus も summary も重ならない指摘（再発番と判定されない）。"""
    return finding(f"m{number}.py::f{number}", f"要約{number}は別の指摘である", **overrides)


class TestIngestStdout(RootedCase):
    prefix = "karte-rep-"

    def setUp(self):
        super().setUp()
        self.ledger_path = self.root / "tmp" / "_karte" / "issue-7.md"

    def _ingest(self, round_no, *blocks):
        code, out, err = self.ingest(round_no, *blocks)
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
                f"  カルテ: {self.ledger_path}",
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
                RESOLVED + "F-7-01",
                "  未解消: F-7-02, F-7-03",
                SCOPE_OUT + "F-7-02",
                UNDECIDED + "F-7-02",
                f"  カルテ: {self.ledger_path}",
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
                RESOLVED + "F-7-01",
                "  未解消: (なし)",
                f"  カルテ: {self.ledger_path}",
            ],
            lines,
        )


class TestOrderOfIdLists(RootedCase):
    """複数 ID の行は ``", "`` 区切りの ID 順。レポートの並びや ``set`` の反復順に依存しない。"""

    prefix = "karte-rep2-"

    def _first_round(self):
        # 3・9 はスコープ外、5・6 は実害なし。残り 8 件が「実害あり・未決定」。
        blocks = [
            ("new", distinct_finding(
                n, scope="out" if n in (3, 9) else "in", **({"harm": "none"} if n in (5, 6) else {})
            ))
            for n in range(1, MANY + 1)
        ]
        code, out, err = self.ingest(1, *blocks)
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        return out.splitlines()

    def test_every_id_list_is_in_id_order(self):
        lines = self._first_round()
        every = ids(*range(1, MANY + 1))
        self.assertIn(f"  新規採番: {every}", lines)
        self.assertIn(f"  未解消: {every}", lines)
        self.assertIn(SCOPE_OUT + ids(3, 9), lines)
        self.assertIn(UNDECIDED + ids(1, 2, 3, 4, 7, 8, 9, 10, 11, 12), lines)

    def test_resolved_ids_are_in_id_order_whatever_order_the_report_lists_them(self):
        self._first_round()
        reposts = [("F-7-%02d" % n, distinct_finding(n, status="resolved")) for n in (10, 2, 7)]
        reposts += [("F-7-%02d" % n, distinct_finding(n)) for n in (12, 1, 9, 4, 11, 3, 8, 5, 6)]
        code, out, err = self.ingest(2, *reposts)
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        lines = out.splitlines()
        self.assertIn(RESOLVED + ids(2, 7, 10), lines)
        self.assertIn("  未解消: " + ids(1, 3, 4, 5, 6, 8, 9, 11, 12), lines)


class TestDistinctFromLine(RootedCase):
    """``distinct_from`` の除外は、ペアごとに ``新 ↔ 旧`` で、``"; "`` 区切り・report の並びで 1 行に出る。"""

    prefix = "karte-rep3-"

    def test_exclusion_pairs_are_listed_exactly_in_one_line(self):
        self.ingest(1, ("new", HARMFUL))
        code, out, err = self.ingest(
            2,
            ("F-7-01", HARMFUL),
            ("new", {**HARMFUL, "distinct_from": "F-7-01"}),
            ("new", {**HARMFUL, "distinct_from": "[F-7-01, F-7-02]"}),
        )
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        lines = out.splitlines()
        pairs = DISTINCT + "F-7-02 ↔ F-7-01; F-7-03 ↔ F-7-01; F-7-03 ↔ F-7-02"
        self.assertEqual([pairs], [line for line in lines if "distinct_from" in line])
        self.assertEqual(["  新規採番: F-7-02, F-7-03", pairs], lines[2:4])  # 「未解消」の前

    def test_no_exclusion_line_without_distinct_from(self):
        code, out, err = self.ingest(1, ("new", HARMFUL))
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        self.assertNotIn("distinct_from", out)


if __name__ == "__main__":
    unittest.main()
