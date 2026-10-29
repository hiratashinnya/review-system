"""通常resolver/proof readerを通し、外部Windows境界だけをrecord/replayする。"""

import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from agy_delegate.cohort_generator import current_generator_sha256
from agy_delegate.cohort_schema import canonical_proof_bytes
from agy_delegate.native_policy import expected_file_only_rules
from agy_delegate.permissions import expected_rules
from agy_delegate.types import Request
from agy_delegate.windows_binding_values import current_binding_values
from agy_delegate.windows_probe import POWERSHELL
from tests.unit.agy_delegate_fixtures import FAKE, synthetic_success
from tests.unit.test_agy_delegate_cohort_fixtures import CohortStoreFixture


class RuntimeCohortFixture(CohortStoreFixture):
    def setUp(self):
        super().setUp()
        patcher = patch.dict("os.environ", {"WSL_DISTRO_NAME": "Synthetic"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.profile = self.home / "Users/synthetic"
        self.exe = self.profile / "AppData/Local/agy/bin/agy.exe"
        self.exe.parent.mkdir(parents=True)
        self.exe.write_text(FAKE)
        self.exe.chmod(0o700)
        self.files = {"global": self.profile / ".gemini/antigravity-cli/settings.json",
                      "project": self.profile / ".gemini/config/projects/default-cli-project.json",
                      "shared": self.profile / ".gemini/config/config.json"}
        for path in self.files.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        self.files["global"].write_text(json.dumps({"permissions": expected_file_only_rules(self.workspace)}))
        self.files["project"].write_text('{"id":"default-cli-project","opaque":{}}')
        self.files["shared"].write_text('{"userSettings":{"opaque":true}}')
        self.settings = self.workspace / "logical-settings.json"
        self.settings.write_text(json.dumps({"permissions": expected_rules(self.workspace)}))
        self.request = Request(self.workspace, self.settings, self.exe,
                               json.dumps({"output": synthetic_success()}),
                               print_timeout=1, caller_state="ready")
        self.counts = {"os": 0, "version": 0, "model": 0}
        self.original_run = subprocess.run
        self.after_version = None
        self.after_os = None
        self.refresh_proof()

    def windows_reply(self, nonce):
        snapshots = {label: {"exists": True, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "acl_sha256": "d" * 64, "owner_sha256": "e" * 64}
                     for label, path in self.files.items()}
        return {"ok": True, "nonce": nonce, "windows_os_sha256": "a" * 64,
                "windows_principal_sha256": "b" * 64,
                "executable_sha256": hashlib.sha256(self.exe.read_bytes()).hexdigest(),
                "files": snapshots, "admin_gateway_candidate_absent": True,
                "gateway_environment_present": False, "update_disabled_for_child": True,
                "os_cwd_observed": False, "settings_writes": 0, "agy_launches": 0}

    def refresh_proof(self):
        now = datetime.now(timezone.utc)
        reply = self.windows_reply("unused")
        self.proof.update(created_utc=(now - timedelta(seconds=1)).isoformat(),
                          expires_utc=(now + timedelta(hours=1)).isoformat(),
                          binding=current_binding_values(self.request, reply), files=reply["files"],
                          generator_source_sha256=current_generator_sha256())
        encoded = canonical_proof_bytes(self.proof, now=now)
        self.digest = hashlib.sha256(encoded).hexdigest()
        self.private_write(self.store / f"{self.digest}.json", encoded)
        self.private_write(self.store / f"{self.wid}.index.json",
                           json.dumps({"protocol": 1, "proof_sha256": self.digest}).encode())

    def boundary(self, argv, **options):
        if argv[0] == POWERSHELL:
            self.counts["os"] += 1
            request = json.loads(options["input"])
            output = json.dumps(self.windows_reply(request["nonce"]))
            if self.after_os:
                self.after_os()
            return subprocess.CompletedProcess(argv, 0, output.encode("utf-8"), b"")
        kind = "version" if "--version" in argv else "model"
        self.counts[kind] += 1
        result = self.original_run(argv, **options)
        if kind == "version" and self.after_version:
            self.after_version()
        return result
