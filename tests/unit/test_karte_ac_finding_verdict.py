"""#801: 未充足・未検証AC finding とround 2での再掲漏れがcleanにならない。"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from karte import ingest_review, model, paths
from karte.exit_codes import EXIT_INCOMPLETE, EXIT_OK
from karte.reviewer_policy import ReviewerIngestPolicy
from karte.status_payload import status_payload
from tests.unit.test_karte_review_summary import CLEAN, FINDING


class ACDispositionVerdictTest(unittest.TestCase):
    def ingest(self, root, number, report, protected=False):
        policy = ReviewerIngestPolicy(root, 801, number) if protected else None
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


if __name__ == "__main__":
    unittest.main()
