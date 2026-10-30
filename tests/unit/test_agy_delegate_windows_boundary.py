"""nonce付きOS読取adapterのclosed schemaと秘密の失敗射影。"""

import copy
import json
import subprocess
from unittest.mock import patch

from agy_delegate.windows_binding_values import validated_windows_reply
from agy_delegate.windows_probe import read_windows_binding
from tests.unit.agy_runtime_cohort_fixture import RuntimeCohortFixture


class WindowsBoundaryTests(RuntimeCohortFixture):
    def test_real_adapter_sends_path_as_data_and_uses_child_environment(self):
        calls = []
        def reply(argv, **options):
            calls.append((argv, options))
            wire = options["input"]
            self.assertIs(type(wire), bytes)
            self.assertFalse(wire.startswith(b"\xef\xbb\xbf"))
            frame = json.loads(wire.decode("utf-8"))
            output = json.dumps(self.windows_reply(frame["nonce"])).encode("utf-8-sig")
            return subprocess.CompletedProcess(argv, 0, output, b"")
        with patch("subprocess.run", side_effect=reply):
            observed = read_windows_binding(self.request)
        argv, options = calls[0]
        self.assertIn("-File", argv)
        self.assertNotIn("-Command", argv)
        self.assertNotIn(self.request.prompt, repr(argv))
        self.assertEqual(options["env"]["AGY_CLI_DISABLE_AUTO_UPDATE"], "true")
        self.assertFalse(observed["os_cwd_observed"])
        self.assertEqual(observed["agy_launches"], 0)

    def test_nonce_unknown_members_and_bool_numeric_coercion_are_rejected(self):
        original = self.windows_reply("nonce")
        variants = [{"nonce": "other"}, {"extra": "private-marker"}, {"settings_writes": False},
                    {"agy_launches": "0"}, {"update_disabled_for_child": "true"},
                    {"gateway_environment_present": True}, {"admin_gateway_candidate_absent": False},
                    {"os_cwd_observed": True}]
        for change in variants:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validated_windows_reply(copy.deepcopy(original) | change, "nonce")

    def test_stderr_failure_and_invalid_json_never_publish_original_message(self):
        for output, errors, status in (("{", "", 0), ("{}", "private-marker /private/path", 0),
                                       ("{}", "", 2)):
            with self.subTest(output=output, status=status):
                completed = subprocess.CompletedProcess([], status, output.encode("utf-8"), errors.encode("utf-8"))
                with patch("subprocess.run", return_value=completed), self.assertRaises(ValueError) as error:
                    read_windows_binding(self.request)
                self.assertEqual(str(error.exception), "cohort_windows_binding_unverified")
