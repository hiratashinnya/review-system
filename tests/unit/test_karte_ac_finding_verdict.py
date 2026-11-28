"""#801: 未充足・未検証AC finding とround 2での再掲漏れがcleanにならない。"""

import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from karte import ingest_review, model, owner_cli, paths
from karte.ac_snapshot import digest, from_issue_body
from karte.exit_codes import EXIT_INCOMPLETE, EXIT_OK
from karte.reviewer_policy import ReviewerIngestPolicy
from karte.status_payload import status_payload
from tests.unit.test_karte_review_summary import CLEAN, DIGEST, FINDING

ISSUE_BODY = "# Issue 801\n\n## Acceptance criteria\n- [ ] 異常系テストを検証する\n"
ACTIVATE = dict(target_key="pr-846", phase="implementation",
                snapshot_oid="a" * 40, input_digest="b" * 64)


class ACDispositionVerdictTest(unittest.TestCase):
    def ingest(self, root, number, report, protected=False):
        policy = ReviewerIngestPolicy(root, 801, number) if protected else None
        if protected:
            # The real owner activation freezes Issue AC before reviewer ingest.
            source = root / "tmp" / "issue.md"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(ISSUE_BODY, encoding="utf-8")
            args = argparse.Namespace(
                repo_root=str(root), issue="801", ac_snapshot_file=str(source),
                repair_declared_scope=False, run_id=f"round-{number}", **ACTIVATE,
            )
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(EXIT_OK, owner_cli.cmd_activate(args))
            expected_digest = digest(from_issue_body(ISSUE_BODY))
            report = report.replace(DIGEST, expected_digest)
            if report.startswith("## Review Summary"):
                # Clean without re-listing the previous open finding still carries
                # a complete AC judgment; it must not silently clear that finding.
                report = (report.replace("ac_count: 0", "ac_count: 1")
                          .replace("<!-- review-complete -->",
                                   "\n### AC 1\nresult: satisfied\n"
                                   "evidence: testcase completed\nfinding_refs: []\n"
                                   "<!-- review-complete -->"))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return ingest_review.ingest_locked(root, 801, number, report, policy)

    def test_unverified_ac_open_real_finding_is_not_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(EXIT_OK, self.ingest(root, 1, FINDING))
            karte = model.parse(paths.read_text(paths.karte_path(801, root)))
            status = status_payload(karte)
            self.assertEqual("harmful-open", status["verdict"])
            self.assertEqual(["F-801-01"], status["undecided_disposition"])

    def test_reviewer_zero_report_with_unresolved_prior_finding_is_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(EXIT_OK, self.ingest(root, 1, FINDING, protected=True))
            self.assertEqual(EXIT_INCOMPLETE, self.ingest(root, 2, CLEAN, protected=True))
            karte = model.parse(paths.read_text(paths.karte_path(801, root)))
            self.assertEqual("open", karte.finding("F-801-01").status)
            self.assertEqual("harmful-open", status_payload(karte)["verdict"])
            self.assertEqual([1, 2], [round.number for round in karte.review_rounds])
            self.assertTrue(all(round.ac_source for round in karte.review_rounds))


if __name__ == "__main__":
    unittest.main()
