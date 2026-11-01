"""``Karte.open_ids`` と ``ingest_checks.find_duplicate`` の特性化（F-696-23）。

* 解消済み（resolved）の finding は ``open_ids`` に入らず、次ラウンドで再掲しなくても拒否されない
  （K-06「不在＝解消ではない」の対象は**未解消**だけ）。
* 同一レポート内の重複（locus が交差し summary が一致する新規 2 件）は ID 再発番で拒否される。
"""

import argparse
import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

from karte import cli, exit_codes, model, paths

ISSUE = 9
_FIELDS = {
    "harm": "real",
    "harm_detail": "検証が素通りして誤った取り込みが通る",
    "severity": "major",
    "scope": "in",
    "evidence": "a/b.py:1 を読み、検査が無いのを確認",
    "expected": "検査が働く",
    "recheck": "該当入力で拒否されることを確認する",
}
FIRST = {**_FIELDS, "locus": "a/b.py::first", "summary": "first が入力検査をしていない"}
SECOND = {**_FIELDS, "locus": "c/d.py::second", "summary": "second が戻り値を握りつぶしている"}
# locus が交差し summary が一致する指摘。同一レポート内の新規 2 件として並べる。
TWIN = {**_FIELDS, "locus": "e/f.py::twin", "summary": "twin が例外を握りつぶして成功を返す"}


def _report(*blocks) -> str:
    parts = []
    for title, fields in blocks:
        parts.append("\n".join([f"### {title}", *(f"{k}: {v}" for k, v in fields.items())]))
    return "\n\n".join(parts) + "\n"


class _IngestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="karte-ic-")).resolve()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        (self.root / "tmp").mkdir()

    def _ingest(self, round_no, *blocks):
        path = self.root / "tmp" / f"review-{round_no}.md"
        path.write_text(_report(*blocks), encoding="utf-8")
        args = argparse.Namespace(
            issue=str(ISSUE), round=str(round_no), source=str(path), repo_root=str(self.root)
        )
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.cmd_ingest_review(args)
        return code, err.getvalue()


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
        text = paths.karte_path(ISSUE, self.root).read_text(encoding="utf-8")
        self.assertEqual([1, 2], model.parse(text).finding("F-9-01").rounds)  # 3 では触られない

    def test_unresolved_finding_missing_from_the_next_report_is_still_refused(self):
        self._ingest(1, ("new", FIRST), ("new", SECOND))
        code, err = self._ingest(2, ("F-9-02", SECOND))
        self.assertEqual(exit_codes.EXIT_ERROR, code)
        self.assertIn("F-9-01", err)


class TestDuplicateWithinOneReport(_IngestCase):
    def test_two_new_findings_describing_the_same_issue_are_refused_as_reissued_ids(self):
        code, err = self._ingest(1, ("new", TWIN), ("new", dict(TWIN)))
        self.assertEqual(exit_codes.EXIT_ERROR, code)
        self.assertIn("ID 再発番", err)
        self.assertFalse(paths.karte_path(ISSUE, self.root).exists())

    def test_distinct_findings_in_one_report_are_accepted(self):
        code, err = self._ingest(1, ("new", FIRST), ("new", SECOND))
        self.assertEqual(exit_codes.EXIT_OK, code, err)


if __name__ == "__main__":
    unittest.main()
