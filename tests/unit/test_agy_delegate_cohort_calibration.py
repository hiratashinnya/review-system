"""校正発行は実reader/publisherを通し、OS境界だけをreplayする。"""

from unittest.mock import patch

from agy_delegate.cohort_calibration import publish_session_calibration
from agy_delegate.cohort_fields import OBSERVATIONS
from agy_delegate.cohort_generator import current_generator_sha256
from agy_delegate.cohort_publication_types import PublicationOutcome
from agy_delegate.cohort_storage import read_cohort
from agy_delegate.runner import run
from agy_delegate.windows_binding_values import current_binding_values
from tests.unit.agy_runtime_cohort_fixture import RuntimeCohortFixture


class CalibrationTests(RuntimeCohortFixture):
    def publish(self, **changes):
        baseline = self.windows_reply("baseline")
        arguments = {"begin_source_sha256": current_generator_sha256(),
                     "baseline_binding": current_binding_values(self.request, baseline),
                     "baseline_files": baseline["files"],
                     "observations": dict.fromkeys(OBSERVATIONS, True), "owner_record_sha256": "a" * 64}
        return publish_session_calibration(self.request, **(arguments | changes))

    def test_real_publication_normal_reader_and_normal_wrapper_connect(self):
        with patch("subprocess.run", side_effect=self.boundary):
            outcome = self.publish()
            proof = read_cohort(self.workspace)
            result = run(self.request)
        self.assertEqual(outcome.state, "committed")
        self.assertTrue(outcome.durability_confirmed)
        self.assertEqual(proof["account_scope"]["declaration"], "personal")
        self.assertEqual(proof["account_scope"]["owner_record_sha256"], "a" * 64)
        self.assertEqual(result.classification, "success_candidate")
        self.assertEqual(self.counts["model"], 1)

    def test_missing_observation_and_source_mismatch_are_before_any_child(self):
        for change in ({"observations": {}}, {"observations": dict.fromkeys(OBSERVATIONS, False)},
                       {"begin_source_sha256": "a" * 64}, {"owner_record_sha256": "private-marker"}):
            with self.subTest(change=change), patch("subprocess.run", side_effect=self.boundary), \
                    self.assertRaises(ValueError):
                self.publish(**change)
        self.assertEqual(self.counts, {"os": 0, "version": 0, "model": 0})

    def test_unknown_global_allow_and_changed_os_snapshot_cannot_publish(self):
        with patch("subprocess.run", side_effect=self.boundary), \
                patch("agy_delegate.cohort_calibration.publish_calibrated_cohort") as publisher:
            self.after_os = lambda: self.files["global"].write_text('{"permissions":{"allow":["read_file(/private-marker)"],"ask":[],"deny":[]}}')
            with self.assertRaises(ValueError) as error:
                self.publish()
            self.assertEqual(str(error.exception), "cohort_calibration_snapshot_unverified")
            publisher.assert_not_called()
        self.assertEqual(self.counts["model"], 0)

    def test_changed_second_binding_and_late_source_do_not_reach_commit(self):
        source = current_generator_sha256()
        first = self.windows_reply("first")
        second = self.windows_reply("second")
        second["windows_principal_sha256"] = "f" * 64
        with patch("agy_delegate.cohort_calibration.read_windows_binding", side_effect=[first, second]), \
                patch("agy_delegate.cohort_calibration.publish_calibrated_cohort") as publisher, \
                self.assertRaisesRegex(ValueError, "^cohort_calibration_changed$"):
            self.publish()
        publisher.assert_not_called()
        with patch("subprocess.run", side_effect=self.boundary), \
                patch("agy_delegate.cohort_calibration.current_generator_sha256", side_effect=[source, "f" * 64]), \
                patch("agy_delegate.cohort_calibration.publish_calibrated_cohort") as publisher, \
                self.assertRaisesRegex(ValueError, "^cohort_generator_mismatch$"):
            self.publish(begin_source_sha256=source)
        publisher.assert_not_called()

    def test_visible_commit_durability_warning_is_returned_without_reclassification(self):
        outcome = PublicationOutcome("committed", "a" * 64, False, "commit_directory_sync")
        with patch("subprocess.run", side_effect=self.boundary), \
                patch("agy_delegate.cohort_calibration.publish_calibrated_cohort", return_value=outcome):
            self.assertIs(self.publish(), outcome)

    def test_witness_baseline_cannot_be_reattributed_to_new_current_snapshot(self):
        baseline = self.windows_reply("baseline")
        binding = current_binding_values(self.request, baseline)
        binding["executable_sha256"] = "f" * 64
        variants = ({"baseline_binding": binding}, {"baseline_files": baseline["files"] | {
            "global": baseline["files"]["global"] | {"sha256": "f" * 64}}})
        for change in variants:
            with self.subTest(change=change), patch("subprocess.run", side_effect=self.boundary), \
                    patch("agy_delegate.cohort_calibration.publish_calibrated_cohort") as publisher, \
                    self.assertRaisesRegex(ValueError, "^cohort_calibration_baseline_mismatch$"):
                self.publish(**change)
            publisher.assert_not_called()
