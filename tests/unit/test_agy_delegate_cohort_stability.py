"""二読間の差替えと proof の filename/content/binding整合を検査する。"""

import hashlib
import json
from unittest.mock import patch

from agy_delegate.cohort_private_io import private_file_bytes
from agy_delegate.cohort_storage import read_cohort
from tests.unit.test_agy_delegate_cohort_fixtures import CohortStoreFixture, NOW


class CohortStabilityTests(CohortStoreFixture):
    def test_same_bytes_with_new_inode_between_reads_are_rejected(self):
        index = self.store / f"{self.wid}.index.json"
        calls = 0
        def replaced(fd, name):
            nonlocal calls
            calls += 1
            if calls == 3:
                pending = self.store / "replacement"
                self.private_write(pending, index.read_bytes())
                pending.replace(index)
            return private_file_bytes(fd, name)
        with patch("agy_delegate.cohort_storage.private_file_bytes", side_effect=replaced):
            with self.assertRaisesRegex(ValueError, "cohort_snapshot_changed"):
                read_cohort(self.workspace, now=NOW)

    def test_proof_hash_cannot_hide_wrong_workspace_binding(self):
        self.proof["binding"]["workspace_wsl_sha256"] = "0" * 64
        self.write_snapshot()
        with self.assertRaisesRegex(ValueError, "cohort_workspace_binding_mismatch"):
            read_cohort(self.workspace, now=NOW)

    def test_valid_hash_of_noncanonical_json_is_rejected(self):
        encoded = json.dumps(self.proof, indent=2).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        self.private_write(self.store / f"{digest}.json", encoded)
        self.private_write(self.store / f"{self.wid}.index.json", json.dumps(
            {"protocol": 1, "proof_sha256": digest}).encode())
        with self.assertRaisesRegex(ValueError, "cohort_proof_noncanonical"):
            read_cohort(self.workspace, now=NOW)

    def test_unreadable_file_error_does_not_leak_os_detail(self):
        with patch("agy_delegate.cohort_private_io.os.open", side_effect=PermissionError("secret")):
            with self.assertRaises(ValueError) as error:
                read_cohort(self.workspace, now=NOW)
        self.assertNotIn("secret", str(error.exception))
