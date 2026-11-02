"""``Karte.open_ids`` と ``ingest_checks`` ／ ``ingest_accept`` の特性化（F-696-23・PR #696 第4回 T05〜T07）。

* 解消済み（resolved）の finding は ``open_ids`` に入らず、次ラウンドで再掲しなくても拒否されない
  （K-06「不在＝解消ではない」の対象は**未解消**だけ）。重複判定（ID 再発番）の比較対象にも入らない。
* 同一レポート内の重複（locus が交差し summary が一致する新規 2 件）は ID 再発番で拒否される。
  ``distinct_from`` は同一レポート内で先に現れたブロックも名指しできる。
* 明示 ID の新規（``F-9-02``）の後ろに置いた ``new`` は、その次の番号を受ける。
"""

import argparse
import contextlib
import io
import unittest

from karte import cli, exit_codes, model, paths
from tests.unit.karte_support import finding, make_tmp_repo, report_text, required_finding

ISSUE = 9
FIRST = finding("a/b.py::first", "first が入力検査をしていない")
SECOND = finding("c/d.py::second", "second が戻り値を握りつぶしている")
# locus が交差し summary が一致する指摘。同一レポート内の新規 2 件として並べる。
TWIN = finding("e/f.py::twin", "twin が例外を握りつぶして成功を返す")


class _IngestCase(unittest.TestCase):
    def setUp(self):
        self.root = make_tmp_repo(self, "karte-ic-")

    def _ingest(self, round_no, *blocks):
        path = self.root / "tmp" / f"review-{round_no}.md"
        path.write_text(report_text(*blocks), encoding="utf-8")
        args = argparse.Namespace(
            issue=str(ISSUE), round=str(round_no), source=str(path), repo_root=str(self.root)
        )
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.cmd_ingest_review(args)
        return code, err.getvalue()

    def _ledger(self) -> model.Karte:
        return model.parse(paths.karte_path(ISSUE, self.root).read_text(encoding="utf-8"))


class TestResolvedFindingsAreNotOpen(_IngestCase):
    def test_open_ids_excludes_resolved_findings(self):
        karte = model.Karte(issue=ISSUE)
        karte.findings.append(model.Finding(id="F-9-01", status="resolved"))
        karte.findings.append(model.Finding(id="F-9-02", status="open"))
        self.assertEqual({"F-9-02"}, karte.open_ids())

    def test_resolved_finding_need_not_be_relisted_in_the_next_round(self):
        self.assertEqual(
            exit_codes.EXIT_OK,
            self._ingest(1, ("new", FIRST), ("new", SECOND))[0],
        )
        resolved = {**FIRST, "status": "resolved"}
        code, err = self._ingest(2, ("F-9-01", resolved), ("F-9-02", SECOND))
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        # F-9-01 は解消済み。ラウンド 3 で再掲しなくても「不在」として拒否されない。
        code, err = self._ingest(3, ("F-9-02", SECOND))
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        self.assertEqual([1, 2], required_finding(self._ledger(), "F-9-01").rounds)  # 3 では触られない

    def test_unresolved_finding_missing_from_the_next_report_is_still_refused(self):
        self._ingest(1, ("new", FIRST), ("new", SECOND))
        code, err = self._ingest(2, ("F-9-02", SECOND))
        self.assertEqual(exit_codes.EXIT_ERROR, code)
        self.assertIn("F-9-01", err)

    def test_new_finding_matching_a_resolved_one_is_accepted_as_new(self):
        """解消済みの指摘と同内容の新規は、再発番ではなく別の新規として受理する。"""
        self._ingest(1, ("new", FIRST))
        self._ingest(2, ("F-9-01", {**FIRST, "status": "resolved"}))
        code, err = self._ingest(3, ("new", FIRST))
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        self.assertEqual("resolved", required_finding(self._ledger(), "F-9-01").status)
        self.assertEqual("open", required_finding(self._ledger(), "F-9-02").status)


class TestDuplicateWithinOneReport(_IngestCase):
    def test_two_new_findings_describing_the_same_issue_are_refused_as_reissued_ids(self):
        code, err = self._ingest(1, ("new", TWIN), ("new", dict(TWIN)))
        self.assertEqual(exit_codes.EXIT_ERROR, code)
        self.assertIn("ID 再発番", err)
        self.assertFalse(paths.karte_path(ISSUE, self.root).exists())

    def test_distinct_findings_in_one_report_are_accepted(self):
        code, err = self._ingest(1, ("new", FIRST), ("new", SECOND))
        self.assertEqual(exit_codes.EXIT_OK, code, err)

    def test_distinct_from_can_name_a_block_that_appeared_earlier_in_the_same_report(self):
        second = {**TWIN, "distinct_from": "F-9-01"}
        code, err = self._ingest(1, ("new", TWIN), ("new", second))
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        self.assertEqual(["F-9-01", "F-9-02"], [item.id for item in self._ledger().findings])

    def test_distinct_from_cannot_name_a_block_that_has_not_appeared_yet(self):
        first = {**TWIN, "distinct_from": "F-9-02"}
        code, err = self._ingest(1, ("new", first), ("new", dict(TWIN)))
        self.assertEqual(exit_codes.EXIT_ERROR, code)
        self.assertIn("実在しない", err)


class TestIdAllocationAfterAnExplicitNewId(_IngestCase):
    def test_new_after_an_explicit_next_id_gets_the_following_number(self):
        self._ingest(1, ("new", FIRST))
        code, err = self._ingest(
            2, ("F-9-01", FIRST), ("F-9-02", SECOND), ("new", TWIN)
        )
        self.assertEqual(exit_codes.EXIT_OK, code, err)
        self.assertEqual(["F-9-01", "F-9-02", "F-9-03"], [i.id for i in self._ledger().findings])
        self.assertEqual("twin が例外を握りつぶして成功を返す", required_finding(self._ledger(), "F-9-03").summary)


if __name__ == "__main__":
    unittest.main()
