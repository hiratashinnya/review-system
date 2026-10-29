"""子workspace/root/論理bytesを本物proofへ別々に束縛する。"""

import json
from dataclasses import replace
from unittest.mock import patch

from agy_delegate.cohort_paths import workspace_id
from agy_delegate.cohort_storage import read_cohort
from agy_delegate.runner import run
from tests.unit.agy_parallel_fixture import ParallelCohortFixture


class ParallelCohortTests(ParallelCohortFixture):
    def test_child_proof_and_root_bind_normal_wrapper_and_record(self):
        request = self.requests[0]
        with patch("subprocess.run", side_effect=self.boundary):
            result = run(request)
        self.assertEqual(result.classification, "success_candidate", result.reasons)
        record = request.workspace / "tmp/agy" / result.run_id / "result.json"
        data = json.loads(record.read_text())
        self.assertEqual(data["workspace"], str(request.workspace))
        self.assertEqual(data["permission_root"], str(self.permission_root))
        self.assertEqual(self.counts["model"], 1)

    def test_root_swap_and_logical_raw_change_stop_before_os_or_agy(self):
        request = self.requests[0]
        variants = [replace(request, permission_root=self.home)]
        with patch("subprocess.run", side_effect=self.boundary):
            for candidate in variants:
                self.assertTrue(run(candidate).reasons)
            self.settings.write_bytes(self.settings.read_bytes() + b"\n")
            self.assertIn("cohort_binding_mismatch", run(request).reasons)
        self.assertEqual(self.counts, {"os": 0, "version": 0, "model": 0})

    def test_child_proof_swap_and_old_binding_shape_have_no_children(self):
        a, b = self.requests
        a_index = self.store / f"{workspace_id(a.workspace)}.index.json"
        b_index = self.store / f"{workspace_id(b.workspace)}.index.json"
        self.private_write(a_index, b_index.read_bytes())
        with patch("subprocess.run", side_effect=self.boundary):
            self.assertTrue(run(a).reasons)
        self.assertEqual(self.counts, {"os": 0, "version": 0, "model": 0})
        proof = read_cohort(b.workspace)
        for key in ("permission_root_wsl_sha256", "permission_root_native_sha256", "logical_settings_sha256"):
            del proof["binding"][key]
        from agy_delegate.cohort_schema import validate_proof
        from datetime import datetime, timezone
        with self.assertRaises(ValueError):
            validate_proof(proof, now=datetime.now(timezone.utc))

    def test_new_allow_union_is_rejected_before_any_child(self):
        data = json.loads(self.settings.read_text())
        data["permissions"]["allow"].append(f"read_file({self.children[0]})")
        self.settings.write_text(json.dumps(data))
        with patch("subprocess.run", side_effect=self.boundary):
            self.assertTrue(run(self.requests[0]).reasons)
        self.assertEqual(self.counts, {"os": 0, "version": 0, "model": 0})
