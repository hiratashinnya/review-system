"""Owner AC GitHub write gate: actual evidence and a simulated remote only."""
import fcntl
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karte import ac_owner_update, ac_snapshot_binding, handoff_header, ingest_receipt, model, paths, review_envelope
from karte.ac_snapshot import digest, from_issue_body
from karte.active_pointer import write_active
from karte.errors import KarteUsageError

BODY = "## Acceptance criteria\n- [ ] AC1\n- [x] AC2\n\n## Notes\nleave this alone\n"


def review_report(round_no, phase):
    expected = review_envelope.expected_of(
        issue=801, phase=phase, run_id=f"run-{round_no}", target_key="801",
        input_digest="b" * 64, snapshot_oid="a" * 40,
    )
    return (handoff_header.render_header(round_no, expected) +
            "\n## Review Summary\n\n### Summary\nfinding_count: 0\nac_count: 2\n"
            f"ac_snapshot_digest: {digest(from_issue_body(BODY))}\n\n"
            "### AC 1\nresult: satisfied\nevidence: tested\nfinding_refs: []\n\n"
            "### AC 2\nresult: satisfied\nevidence: tested\nfinding_refs: []\n"
            "<!-- review-complete -->\n")


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
        ledger = model.new_karte(801)
        ingest_receipt.record(ledger, 1, review_report(1, "implementation"), self.root, 801, ac_snapshot=frozen)
        paths.write_text_atomic(paths.karte_path(801, self.root), model.dumps(ledger))
        write_active(self.root, 801, 1)

    def run_update(self, remote, **kwargs):
        return ac_owner_update.perform(self.root, 801, 1, self.snapshot,
                                       "hiratashinnya/review-system", remote=remote, **kwargs)

    def test_writer_lock_is_held_across_every_github_call(self):
        # Regression (Codex P2 r4681303847): a concurrent karte writer must not get in
        # between round verification and read-back, so every remote call probes the lock.
        lock_path = paths.karte_dir(self.root) / ".writer.lock"
        inner = Remote()
        observed = []

        def probing_remote(host, repository, issue, *, new_body=None):
            fd = os.open(lock_path, os.O_RDWR)
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    observed.append("free")
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except BlockingIOError:
                    observed.append("held")
            finally:
                os.close(fd)
            return inner(host, repository, issue, new_body=new_body)

        changed = self.run_update(probing_remote)
        self.assertEqual(changed, [1])
        self.assertEqual(inner.writes, 1)
        self.assertEqual(observed, ["held"] * len(observed))
        self.assertEqual(len(observed), 4)

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

    def test_cancelled_source_with_same_ac_is_rejected_before_api(self):
        other_body = BODY.replace("leave this alone", "different notes outside AC")
        other_input = self.root / "tmp" / "cancelled.md"
        other_input.write_text(other_body, encoding="utf-8")
        cancelled = ac_snapshot_binding.stage(self.root, 801, 1, other_input)
        self.assertNotEqual(self.snapshot, cancelled["source"])
        self.assertEqual(cancelled["digest"], digest(from_issue_body(BODY)))
        remote = Remote()
        with self.assertRaisesRegex(KarteUsageError, "受理済みround"):
            ac_owner_update.perform(self.root, 801, 1, cancelled["source"],
                                    "hiratashinnya/review-system", remote=remote)
        self.assertEqual((0, 0), (remote.reads, remote.writes))

    def test_legacy_receipt_without_binding_cannot_write_ac(self):
        ledger = model.parse(paths.read_text(paths.karte_path(801, self.root)))
        rec = ledger.review_rounds[0]
        ledger.review_rounds = [type(rec)(rec.number, rec.digest, rec.source)]
        paths.write_text_atomic(paths.karte_path(801, self.root), model.dumps(ledger))
        remote = Remote()
        with self.assertRaises(KarteUsageError):
            self.run_update(remote)
        self.assertEqual((0, 0), (remote.reads, remote.writes))

    def test_prior_test_design_ac_receipt_is_retained_and_cannot_write(self):
        ledger_path = paths.karte_path(801, self.root)
        ledger = model.parse(paths.read_text(ledger_path))
        frozen = ac_snapshot_binding.stage(self.root, 801, 2, self.root / self.snapshot)
        report = review_report(2, "test_design")
        ingest_receipt.record(ledger, 2, report, self.root, 801, ac_snapshot=frozen)
        paths.write_text_atomic(ledger_path, model.dumps(ledger))
        write_active(self.root, 801, 2)
        original = ingest_receipt.original_path(self.root, 801, 2)
        before = ledger_path.read_bytes()
        remote = Remote()
        with self.assertRaisesRegex(KarteUsageError, "2b"):
            ac_owner_update.perform(self.root, 801, 2, frozen["source"],
                                    "hiratashinnya/review-system", dry_run=True, remote=remote)
        self.assertEqual((0, 0), (remote.reads, remote.writes))
        self.assertEqual(before, ledger_path.read_bytes())
        self.assertEqual(report, original.read_text(encoding="utf-8"))

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
