"""cohort 試験だけが使用する偽校正 proof と private home。"""

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agy_delegate.cohort_fields import BINDING_ENUMS, BINDING_HASHES, OBSERVATIONS
from agy_delegate.cohort_paths import _check_directory, workspace_id
from agy_delegate.cohort_schema import canonical_proof_bytes

NOW = datetime(2026, 10, 28, 1, tzinfo=timezone.utc)


def fake_proof(workspace: Path) -> dict:
    binding = {key: "a" * 64 for key in BINDING_HASHES} | BINDING_ENUMS
    binding["workspace_wsl_sha256"] = workspace_id(workspace)
    absent = {"exists": False, "sha256": None, "acl_sha256": None, "owner_sha256": None}
    return {"protocol": 1, "created_utc": NOW.isoformat(),
            "expires_utc": (NOW + timedelta(hours=24)).isoformat(),
            "generator_source_sha256": "b" * 64, "binding": binding,
            "files": {"global": {"exists": True, "sha256": "c" * 64,
                                 "acl_sha256": "d" * 64, "owner_sha256": "e" * 64},
                      "project": absent.copy(), "shared": absent.copy()},
            "observations": dict.fromkeys(OBSERVATIONS, True),
            "account_scope": {"declaration": "personal", "owner_record_sha256": "f" * 64}}


class CohortStoreFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.workspace = self.home / "workspace"
        self.workspace.mkdir()
        self.wid = workspace_id(self.workspace)
        self.proof = fake_proof(self.workspace)
        self.store = self.home / ".local/state/agy-delegate/cohorts/v1"
        self.store.mkdir(parents=True, mode=0o700)
        for directory in self.store.parents:
            if directory == self.home:
                break
            directory.chmod(0o700)
        for patcher in [patch("agy_delegate.cohort_paths.pwd.getpwuid",
                              return_value=SimpleNamespace(pw_dir=str(self.home))),
                        patch("agy_delegate.cohort_paths._check_directory",
                              side_effect=self.check_fixture)]:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.digest = self.write_snapshot()

    def check_fixture(self, info, policy):
        if policy != "ancestor":
            _check_directory(info, policy)

    def private_write(self, path: Path, content: bytes):
        path.write_bytes(content)
        path.chmod(0o600)

    def write_snapshot(self):
        encoded = canonical_proof_bytes(self.proof, now=NOW)
        digest = hashlib.sha256(encoded).hexdigest()
        self.private_write(self.store / f"{digest}.json", encoded)
        self.private_write(self.store / f"{self.wid}.index.json", json.dumps(
            {"protocol": 1, "proof_sha256": digest}).encode())
        return digest
