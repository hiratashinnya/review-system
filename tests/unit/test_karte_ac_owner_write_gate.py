"""Owner AC GitHub write gate: actual evidence and a simulated remote only."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karte import ac_owner_update, ac_snapshot_binding, ingest_receipt, model, paths
from karte.ac_snapshot import digest, from_issue_body
from karte.active_pointer import write_active
from karte.errors import KarteUsageError

BODY = "## Acceptance criteria\n- [ ] AC1\n- [x] AC2\n\n## Notes\nleave this alone\n"


class Remote:
    def __init__(self, body=BODY, drift=False, readback_error=False):
        self.body, self.drift, self.readback_error = body, drift, readback_error
        self.reads = self.writes = 0

    def __call__(self, host, repository, issue, *, new_body=None):
        assert (host, repository, issue) == ("github.com", "hiratashinnya/review-system", 801)
        if new_body is not None:
            self.writes += 1
            self.body = new_body
            return new_body
        self.reads += 1
        if self.drift and self.reads == 2:
            self.body = self.body.replace("leave this alone", "external concurrent edit")
        if self.readback_error and self.writes:
            return "other writer changed the Issue after PATCH"
        return self.body


class OwnerWriteGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        origin = patch("karte.ac_repository.checkout_origin", return_value={"host": "github.com", "repository": "hiratashinnya/review-system"})
        origin.start()
        self.addCleanup(origin.stop)
        (self.root / "tmp").mkdir()
        source = self.root / "tmp" / "frozen.md"
        source.write_text(BODY, encoding="utf-8")
        frozen = ac_snapshot_binding.stage(self.root, 801, 1, source)
        self.snapshot = frozen["source"]
        report = ("## Review Summary\n\n### Summary\nfinding_count: 0\nac_count: 2\n"
                  f"ac_snapshot_digest: {digest(from_issue_body(BODY))}\n\n"
                  "### AC 1\nresult: satisfied\nevidence: tested\nfinding_refs: []\n\n"
                  "### AC 2\nresult: satisfied\nevidence: tested\nfinding_refs: []\n"
                  "<!-- review-complete -->\n")
        ledger = model.new_karte(801)
        ingest_receipt.record(ledger, 1, report, self.root, 801)
        paths.write_text_atomic(paths.karte_path(801, self.root), model.dumps(ledger))
        write_active(self.root, 801, 1)

    def run_update(self, remote, **kwargs):
        return ac_owner_update.perform(self.root, 801, 1, self.snapshot,
                                       "hiratashinnya/review-system", remote=remote, **kwargs)

    def test_only_satisfied_checkbox_is_written_and_read_back(self):
        remote = Remote()
        self.assertEqual([1], self.run_update(remote))
        self.assertEqual(1, remote.writes)
        self.assertEqual(3, remote.reads)
        self.assertIn("- [x] AC1", remote.body)
        self.assertIn("- [x] AC2", remote.body)
        self.assertIn("leave this alone", remote.body)

    def test_dry_run_and_noop_are_read_only(self):
        dry = Remote()
        self.assertEqual([1], self.run_update(dry, dry_run=True))
        self.assertEqual(0, dry.writes)
        already = Remote(BODY.replace("- [ ] AC1", "- [x] AC1"))
        with self.assertRaises(KarteUsageError):
            self.run_update(already)
        self.assertEqual(0, already.writes)

    def test_ac_drift_or_non_ac_race_aborts_before_write(self):
        for remote in (Remote(BODY.replace("AC2", "changed AC2")), Remote(drift=True)):
            with self.subTest(remote=remote), self.assertRaises(KarteUsageError):
                self.run_update(remote)
            self.assertEqual(0, remote.writes)

    def test_readback_mismatch_reports_failure_after_patch(self):
        remote = Remote(readback_error=True)
        with self.assertRaises(KarteUsageError):
            self.run_update(remote)
        self.assertEqual(1, remote.writes)

    def test_wrong_repository_is_rejected_before_any_github_api_call(self):
        for wrong in ("wrong-owner/unrelated", "other/review-system", "invalid repo"):
            with self.subTest(repository=wrong):
                remote = Remote()
                with self.assertRaisesRegex(KarteUsageError, "repository"):
                    ac_owner_update.perform(self.root, 801, 1, self.snapshot,
                                            wrong, remote=remote)
                self.assertEqual((0, 0), (remote.reads, remote.writes))

    def test_repository_binding_tamper_or_missing_is_rejected_without_api(self):
        sidecar = self.root / (self.snapshot + ".repository.json")
        original = sidecar.read_text(encoding="utf-8")
        for replacement in ('{"host":"evil.example","repository":"hiratashinnya/review-system"}\n',
                            '{"host":"github.com","repository":"wrong-owner/unrelated"}\n',
                            '{"repository":"hiratashinnya/review-system"}\n', 'invalid json', None):
            with self.subTest(replacement=replacement):
                if replacement is None:
                    sidecar.unlink()
                else:
                    sidecar.write_text(replacement, encoding="utf-8")
                remote = Remote()
                with self.assertRaises(KarteUsageError):
                    self.run_update(remote)
                self.assertEqual((0, 0), (remote.reads, remote.writes))
                sidecar.write_text(original, encoding="utf-8")

    def test_wrong_round_or_tampered_snapshot_or_receipt_fails_closed(self):
        remote = Remote()
        with self.assertRaises(KarteUsageError):
            ac_owner_update.perform(self.root, 801, 2, self.snapshot,
                                    "hiratashinnya/review-system", remote=remote)
        snapshot = self.root / self.snapshot
        snapshot.write_text("tampered", encoding="utf-8")
        with self.assertRaises(KarteUsageError):
            self.run_update(remote)
        self.assertEqual(0, remote.writes)


if __name__ == "__main__":
    unittest.main()
