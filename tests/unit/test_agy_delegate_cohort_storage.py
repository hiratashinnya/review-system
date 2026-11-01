"""実ファイルによるcohort読取、marker/改変/非正規入力の拒否。"""

import json
from datetime import timedelta
from unittest.mock import patch

from agy_delegate.cohort_storage import read_cohort
from tests.unit.test_agy_delegate_cohort_fixtures import CohortStoreFixture, NOW


class CohortStorageTests(CohortStoreFixture):
    def test_valid_private_snapshot_is_read_without_any_subprocess(self):
        with patch("subprocess.run") as child:
            self.assertEqual(read_cohort(self.workspace, now=NOW), self.proof)
        child.assert_not_called()

    def test_missing_marker_index_or_proof_never_uses_old_proof(self):
        index = self.store / f"{self.wid}.index.json"
        proof = self.store / f"{self.digest}.json"
        for path in [index, proof]:
            content = path.read_bytes()
            path.unlink()
            with self.assertRaises(ValueError):
                read_cohort(self.workspace, now=NOW)
            self.private_write(path, content)
        marker = self.store / f"{self.wid}.publishing"
        marker.mkdir()
        with self.assertRaisesRegex(ValueError, "cohort_publication_pending"):
            read_cohort(self.workspace, now=NOW)

    def test_permission_symlink_hardlink_directory_and_fifo_fail_closed(self):
        import os
        index = self.store / f"{self.wid}.index.json"
        saved = index.read_bytes()
        index.chmod(0o644)
        with self.assertRaises(ValueError):
            read_cohort(self.workspace, now=NOW)
        index.chmod(0o600)
        link = self.store / "alias"
        os.link(index, link)
        with self.assertRaises(ValueError):
            read_cohort(self.workspace, now=NOW)
        link.unlink()
        for kind in ["symlink", "directory", "fifo"]:
            index.unlink()
            if kind == "symlink":
                index.symlink_to(self.store / f"{self.digest}.json")
            elif kind == "directory":
                index.mkdir()
            else:
                os.mkfifo(index, mode=0o600)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                read_cohort(self.workspace, now=NOW)
            index.rmdir() if kind == "directory" else index.unlink()
            self.private_write(index, saved)

    def test_duplicate_unknown_and_nonfinite_json_are_rejected(self):
        index = self.store / f"{self.wid}.index.json"
        variants = [b'{"protocol":1,"protocol":1,"proof_sha256":"' + self.digest.encode() + b'"}',
                    json.dumps({"protocol": 1, "proof_sha256": self.digest, "extra": None}).encode(),
                    b'{"protocol":NaN,"proof_sha256":"' + self.digest.encode() + b'"}', b"\xff"]
        for content in variants:
            self.private_write(index, content)
            with self.assertRaises(ValueError):
                read_cohort(self.workspace, now=NOW)

    def test_changed_proof_or_oversize_or_expiry_cannot_be_accepted(self):
        proof = self.store / f"{self.digest}.json"
        original = proof.read_bytes()
        for content in [original + b" ", b"x" * 65537]:
            self.private_write(proof, content)
            with self.assertRaises(ValueError):
                read_cohort(self.workspace, now=NOW)
        self.private_write(proof, original)
        with self.assertRaises(ValueError):
            read_cohort(self.workspace, now=NOW + timedelta(hours=24))

    def test_marker_created_during_read_is_detected(self):
        from agy_delegate.cohort_storage import _read_pair
        def changed(*args):
            result = _read_pair(*args)
            (self.store / f"{self.wid}.publishing").touch(mode=0o600)
            return result
        with patch("agy_delegate.cohort_storage._read_pair", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "cohort_publication_pending"):
                read_cohort(self.workspace, now=NOW)
