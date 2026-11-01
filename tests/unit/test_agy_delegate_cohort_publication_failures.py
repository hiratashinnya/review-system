"""各 fsync/replace/unlink 故障を実fileで注入し虚偽rollbackを防ぐ。"""

import os
from unittest.mock import patch

from agy_delegate.cohort_publication import publish_calibrated_cohort
from agy_delegate.cohort_storage import read_cohort
from tests.unit.test_agy_delegate_cohort_fixtures import CohortStoreFixture, NOW


class CohortPublicationFailureTests(CohortStoreFixture):
    def test_each_precommit_sync_failure_keeps_marker_and_stops_reader(self):
        marker = self.store / f"{self.wid}.publishing"
        real_sync = os.fsync
        for fail_at in range(1, 7):
            count = 0
            def fault(fd):
                nonlocal count
                count += 1
                if count == fail_at:
                    raise OSError("private detail")
                return real_sync(fd)
            with patch("agy_delegate.cohort_publication.os.fsync", side_effect=fault):
                outcome = publish_calibrated_cohort(self.workspace, self.proof, now=NOW)
            with self.subTest(fail_at=fail_at):
                self.assertEqual(outcome.state, "pending")
                self.assertIsNone(outcome.proof_sha256)
                self.assertFalse(outcome.durability_confirmed)
                self.assertTrue(marker.exists())
                self.assertNotIn("private", repr(outcome))
                with self.assertRaisesRegex(ValueError, "cohort_publication_pending"):
                    read_cohort(self.workspace, now=NOW)
            marker.unlink()

    def test_final_sync_failure_is_visible_commit_with_durability_warning_state(self):
        real_sync = os.fsync
        count = 0
        def fault(fd):
            nonlocal count
            count += 1
            if count == 7:
                raise OSError("private detail")
            return real_sync(fd)
        with patch("agy_delegate.cohort_publication.os.fsync", side_effect=fault):
            outcome = publish_calibrated_cohort(self.workspace, self.proof, now=NOW)
        self.assertEqual(outcome.state, "committed")
        self.assertEqual(outcome.proof_sha256, self.digest)
        self.assertFalse(outcome.durability_confirmed)
        self.assertEqual(outcome.phase, "commit_directory_sync")
        self.assertFalse((self.store / f"{self.wid}.publishing").exists())
        self.assertEqual(read_cohort(self.workspace, now=NOW), self.proof)

    def test_replace_and_marker_unlink_failure_are_pending(self):
        marker = self.store / f"{self.wid}.publishing"
        for operation, phase in [("replace", "index_replace"), ("unlink", "marker_unlink")]:
            with patch(f"agy_delegate.cohort_publication.os.{operation}", side_effect=OSError("secret")):
                outcome = publish_calibrated_cohort(self.workspace, self.proof, now=NOW)
            self.assertEqual((outcome.state, outcome.phase), ("pending", phase))
            self.assertTrue(marker.exists())
            with self.assertRaises(ValueError):
                read_cohort(self.workspace, now=NOW)
            marker.unlink()

    def test_readback_failure_does_not_remove_marker_or_reuse_old_index(self):
        before = (self.store / f"{self.wid}.index.json").read_bytes()
        with patch("agy_delegate.cohort_publication_io.private_file_bytes",
                   return_value=(b"corrupt", ())):
            outcome = publish_calibrated_cohort(self.workspace, self.proof, now=NOW)
        self.assertEqual(outcome.state, "pending")
        self.assertEqual(before, (self.store / f"{self.wid}.index.json").read_bytes())
        with self.assertRaises(ValueError):
            read_cohort(self.workspace, now=NOW)
