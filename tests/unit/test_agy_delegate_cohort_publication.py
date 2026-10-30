"""private publication の commitpoint と新校正未成立の区別。"""

import os
from unittest.mock import patch

from agy_delegate.cohort_publication import publish_calibrated_cohort
from agy_delegate.cohort_storage import read_cohort
from tests.unit.test_agy_delegate_cohort_fixtures import CohortStoreFixture, NOW


class CohortPublicationTests(CohortStoreFixture):
    def test_publish_success_exposes_only_verified_snapshot_and_private_modes(self):
        self.proof["generator_source_sha256"] = "2" * 64
        result = publish_calibrated_cohort(self.workspace, self.proof, now=NOW)
        self.assertEqual(result.state, "committed")
        self.assertTrue(result.durability_confirmed)
        self.assertEqual(result.phase, "complete")
        self.assertEqual(read_cohort(self.workspace, now=NOW), self.proof)
        self.assertFalse((self.store / f"{self.wid}.publishing").exists())
        for path in self.store.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.stat().st_uid, os.getuid())

    def test_invalid_schema_or_wrong_workspace_has_no_storage_effect(self):
        before = {p.name: p.read_bytes() for p in self.store.iterdir()}
        for field, value in [("protocol", True), ("raw_settings", "forbidden")]:
            invalid = self.proof | {field: value}
            with self.assertRaises(ValueError):
                publish_calibrated_cohort(self.workspace, invalid, now=NOW)
        self.proof["binding"]["workspace_wsl_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            publish_calibrated_cohort(self.workspace, self.proof, now=NOW)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.store.iterdir()})

    def test_existing_marker_collision_is_not_started_and_never_falls_back(self):
        marker = self.store / f"{self.wid}.publishing"
        marker.mkdir()
        index = (self.store / f"{self.wid}.index.json").read_bytes()
        outcome = publish_calibrated_cohort(self.workspace, self.proof, now=NOW)
        self.assertEqual((outcome.state, outcome.proof_sha256), ("not_started", None))
        self.assertEqual(outcome.phase, "marker_create")
        self.assertEqual(index, (self.store / f"{self.wid}.index.json").read_bytes())
        self.assertTrue(marker.is_dir())
        with self.assertRaisesRegex(ValueError, "cohort_publication_pending"):
            read_cohort(self.workspace, now=NOW)

    def test_existing_wrong_mode_or_content_proof_keeps_marker_pending(self):
        proof = self.store / f"{self.digest}.json"
        proof.chmod(0o644)
        outcome = publish_calibrated_cohort(self.workspace, self.proof, now=NOW)
        self.assertEqual((outcome.state, outcome.proof_sha256), ("pending", None))
        self.assertEqual(outcome.phase, "proof_write_verify_sync")
        self.assertTrue((self.store / f"{self.wid}.publishing").exists())

    def test_existing_proof_reuse_syncs_file_before_final_commit(self):
        events = []
        original_sync, original_unlink = os.fsync, os.unlink
        def synced(fd):
            events.append("sync")
            return original_sync(fd)
        def unlinked(name, **kwargs):
            events.append("unlink")
            return original_unlink(name, **kwargs)
        with patch("agy_delegate.cohort_publication.os.fsync", side_effect=synced), patch(
            "agy_delegate.cohort_publication.os.unlink", side_effect=unlinked
        ):
            outcome = publish_calibrated_cohort(self.workspace, self.proof, now=NOW)
        self.assertTrue(outcome.durability_confirmed)
        self.assertEqual(events, ["sync"] * 6 + ["unlink", "sync"])
