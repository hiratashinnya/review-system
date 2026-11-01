"""runner→実candidate resolver→decoderを偽Windows配置だけで接続する。"""

import hashlib
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from agy_delegate.runner import run
from agy_delegate.settings_reads import read_layer_permissions
from agy_delegate.settings_sources import resolve_candidate_sources
from tests.unit.agy_delegate_fixtures import FakeWorkspace


class RuntimeCandidateTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWorkspace()
        self.addCleanup(self.fake.close)
        self.profile = self.fake.workspace / "Users" / "synthetic-user"
        self.exe = self.profile / "AppData/Local/agy/bin/agy.exe"
        self.exe.parent.mkdir(parents=True)
        self.exe.write_bytes(b"synthetic-not-executed")
        self.exe.chmod(0o700)
        self.global_file = self.profile / ".gemini/antigravity-cli/settings.json"
        self.global_file.parent.mkdir(parents=True)
        self.request = replace(self.fake.request(), executable=self.exe)

    def assert_no_launch(self):
        before = hashlib.sha256(self.global_file.read_bytes()).digest()
        with patch("agy_delegate.runner.execute") as execute, \
                patch("agy_delegate.version.subprocess.run") as subprocess:
            result = run(self.request)
        execute.assert_not_called()
        subprocess.assert_not_called()
        self.assertEqual(hashlib.sha256(self.global_file.read_bytes()).digest(), before)
        self.assertNotIn(str(self.profile), repr(result.reasons))
        self.assertNotIn("private-rule-marker", repr(result.reasons))
        return result.reasons

    def test_fixed_candidates_do_not_use_request_settings_or_cache(self):
        layers = resolve_candidate_sources(self.exe).layers
        self.assertEqual([layer.name for layer in layers], ["global", "project", "shared_user", "admin"])
        self.assertEqual(layers[1].path, self.profile / ".gemini/config/projects/default-cli-project.json")
        self.assertEqual(layers[2].path, self.profile / ".gemini/config/config.json")
        self.assertIsNone(layers[3].path)
        self.assertNotIn(self.request.settings, [layer.path for layer in layers])

    def test_unknown_admin_does_not_hide_known_excessive_allow_ask_and_duplicate(self):
        self.global_file.write_text(json.dumps({"permissions": {
            "allow": ["command(private-rule-marker)"] * 2,
            "ask": ["write_file(private-rule-marker)"], "deny": ["read_file(private-rule-marker)"]}}))
        reasons = self.assert_no_launch()
        for group in ("allow", "ask", "deny"):
            self.assertIn("unreviewed_or_conflicting_rules:" + group, reasons)
        self.assertIn("settings_layer_duplicate_rules:global:allow", reasons)
        self.assertIn("settings_admin_presence_or_precedence_unverified", reasons)
        self.assertFalse(any(reason.startswith("missing_rules:") for reason in reasons))

    def test_invalid_json_duplicate_key_unknown_schema_and_symlink_never_launch(self):
        for raw in ('{', '{"permissions":{},"permissions":{}}',
                    '{"permissions":{"unknown":[]}}', '{"permissions":{"allow":false}}'):
            with self.subTest(raw=raw):
                self.global_file.write_text(raw)
                self.assertTrue(self.assert_no_launch())
        self.global_file.write_text('{}')
        alias = self.global_file.with_name("alias.json")
        alias.symlink_to(self.global_file)
        layer = replace(resolve_candidate_sources(self.exe).layers[0], path=alias)
        self.assertIn("settings_layer_symlink_unsupported:global", read_layer_permissions(layer)[2])

    def test_observed_home_shim_resolves_only_to_fixed_layout_candidate(self):
        home = self.fake.workspace / "synthetic-home"
        shim = home / ".local/bin/agy"
        shim.parent.mkdir(parents=True)
        shim.symlink_to(self.exe)
        with patch("pathlib.Path.home", return_value=home):
            self.assertEqual(resolve_candidate_sources(shim).layers[0].path, self.global_file)
        unknown = shim.with_name("other-agy")
        unknown.symlink_to(self.exe)
        self.assertIn("settings_executable_symlink_unsupported", resolve_candidate_sources(unknown).reasons)

    def test_cyclic_home_shim_returns_fixed_reason_without_launch_or_path(self):
        home = self.fake.workspace / "synthetic-home"
        shim = home / ".local/bin/agy"
        shim.parent.mkdir(parents=True)
        shim.symlink_to(shim)
        self.global_file.write_text('{}')
        self.request = replace(self.request, executable=shim)
        with patch("pathlib.Path.home", return_value=home):
            reasons = self.assert_no_launch()
            resolution = resolve_candidate_sources(shim)
        self.assertIn("executable_unavailable", reasons)
        self.assertIn("settings_executable_alias_unresolvable", resolution.reasons)
        self.assertNotIn(str(shim), repr(reasons))

