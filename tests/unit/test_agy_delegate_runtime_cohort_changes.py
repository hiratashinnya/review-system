"""検査間のexe/source/settings変更で版・promptを起動しない。"""

import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from agy_delegate.runner import run
from tests.unit.agy_runtime_cohort_fixture import RuntimeCohortFixture


class RuntimeCohortChangeTests(RuntimeCohortFixture):
    def other_source(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "synthetic.py").write_text("synthetic_source = True\n")
        return root

    def test_new_executable_bytes_fail_before_even_os_probe(self):
        changed = self.exe.read_text() + "\n# changed binary content\n"
        self.exe.write_text(changed)
        with patch("subprocess.run", side_effect=self.boundary):
            result = run(self.request)
        self.assertIn("cohort_binding_mismatch", result.reasons)
        self.assertEqual(sum(self.counts.values()), 0)
        self.assertEqual(self.exe.read_text(), changed)

    def test_unregistered_source_closure_fails_before_os_probe(self):
        with patch("agy_delegate.cohort_generator._PACKAGE_DIRECTORY", self.other_source()), \
                patch("subprocess.run", side_effect=self.boundary):
            result = run(self.request)
        self.assertIn("cohort_generator_mismatch", result.reasons)
        self.assertEqual(sum(self.counts.values()), 0)

    def test_executable_changed_after_os_snapshot_never_gets_version_query(self):
        original = self.exe.read_text()
        self.after_os = lambda: self.exe.write_text(original + "\n# late change\n")
        with patch("subprocess.run", side_effect=self.boundary):
            result = run(self.request)
        self.assertIn("cohort_binding_mismatch", result.reasons)
        self.assertEqual(self.counts, {"os": 1, "version": 0, "model": 0})

    def test_settings_changed_while_waiting_for_lock_prevent_version_query(self):
        @contextmanager
        def changed_lock(*args, **kwargs):
            self.files["global"].write_text('{"permissions":{"allow":["command(regex:.*)"]}}')
            yield
        with patch("agy_delegate.runner.execution_lock", changed_lock), \
                patch("subprocess.run", side_effect=self.boundary):
            result = run(self.request)
        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(self.counts, {"os": 1, "version": 0, "model": 0})

    def test_final_actual_version_check_cannot_be_replaced_by_proof_claim(self):
        self.exe.write_text(self.exe.read_text().replace("print('1.4.8')", "print('9.9.9')"))
        self.refresh_proof()
        with patch("subprocess.run", side_effect=self.boundary):
            result = run(self.request)
        self.assertIn("agy_version_unverified_or_mismatch", result.reasons)
        self.assertEqual(self.counts, {"os": 2, "version": 1, "model": 0})
