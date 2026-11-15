"""Issue #801: Review Summary と finding 0件取り込みの回帰テスト。"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from karte import ingest_review, model, paths, review_summary
from karte.exit_codes import EXIT_ERROR, EXIT_OK

DIGEST = "a" * 64
CLEAN = (
    "## Review Summary\n\n### Summary\n"
    "finding_count: 0\nac_count: 0\nac_snapshot_digest: " + DIGEST
    + "\n<!-- review-complete -->\n"
)
FINDING = (
    "## Findings\n\n### new\n"
    "harm: real\nharm_detail: 必要な異常系テストの記録が存在しない\n"
    "severity: major\nscope: in\nlocus: tests/unit\n"
    "summary: ACの異常系テストが未検証\n"
    "evidence: 実行結果が確認できない\n"
    "expected: 異常系テストが成功する\nrecheck: テストを実行する\n"
    "status: open\n\n## Review Summary\n\n### Summary\n"
    "finding_count: 1\nac_count: 1\nac_snapshot_digest: " + DIGEST + "\n"
    "\n### AC 1\nresult: unverified\nevidence: 実測が必要\n"
    "finding_refs: [new@1]\n<!-- review-complete -->\n"
)


class ReviewSummaryTest(unittest.TestCase):
    def test_clean_summary_without_findings(self):
        summary = review_summary.parse_summary(CLEAN, 801)
        self.assertEqual(summary.finding_count, 0)
        self.assertEqual(summary.ac_count, 0)
        self.assertEqual(model.parse_review(CLEAN, 801), [])

    def test_nonzero_summary_with_unverified_ac(self):
        summary = review_summary.parse_summary(FINDING, 801)
        self.assertEqual(summary.judgments[0].result, "unverified")
        self.assertEqual(summary.judgments[0].finding_refs, ("new@1",))
        self.assertEqual(len(model.parse_review(FINDING, 801)), 1)

    def test_incomplete_and_inconsistent_reports_fail_closed(self):
        cases = [
            CLEAN.replace("<!-- review-complete -->", ""),
            CLEAN.replace("finding_count: 0", "finding_count: 1"),
            CLEAN.replace("ac_count: 0", "ac_count: 1"),
            CLEAN.replace(DIGEST, "invalid"),
            CLEAN.replace("### Summary", "### Other"),
            FINDING.replace("finding_refs: [new@1]", "finding_refs: [new@2]"),
            FINDING.replace("harm: real", "harm: none"),
            FINDING.replace("result: unverified", "result: satisfied"),
            FINDING.replace("result: unverified", "result: [x]"),
            FINDING.replace("ac_count: 1", "ac_count: 2"),
            "## Review Summary\n",
        ]
        for case in cases:
            with self.subTest(case=case[:90]), self.assertRaises(model.KarteFormatError):
                model.parse_review(case, 801)

    def test_ingest_zero_round_records_receipt_and_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = ingest_review.ingest_locked(root, 801, 1, CLEAN)
            self.assertEqual(code, EXIT_OK)
            ledger = model.parse(paths.read_text(paths.karte_path(801, root)))
            self.assertEqual(len(ledger.findings), 0)
            self.assertEqual([r.number for r in ledger.review_rounds], [1])
            receipt = ledger.review_rounds[0]
            self.assertEqual(receipt.source, "tmp/_karte/issue-801-review-round-1.md")
            archived = paths.read_text(paths.resolve_within_repo(root / receipt.source, root))
            self.assertEqual(archived, CLEAN)
            from hashlib import sha256
            self.assertEqual(receipt.digest, sha256(archived.encode("utf-8")).hexdigest())

    def test_previous_open_finding_is_not_silently_resolved_by_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                first = ingest_review.ingest_locked(root, 801, 1, FINDING)
                second = ingest_review.ingest_locked(root, 801, 2, CLEAN)
            self.assertEqual(first, EXIT_OK)
            self.assertEqual(second, EXIT_ERROR)
            ledger = model.parse(paths.read_text(paths.karte_path(801, root)))
            self.assertEqual([r.number for r in ledger.review_rounds], [1])
            self.assertEqual(ledger.findings[0].status, "open")


if __name__ == "__main__":
    unittest.main()
