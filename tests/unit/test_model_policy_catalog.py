"""認証もモデル推論も使わず一覧取得の停止条件を検査する。"""

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from model_policy.catalog import codex_catalog, copilot_catalog


class CatalogTests(unittest.TestCase):
    def test_codex_invocation_filters_unavailable_entries(self):
        runner = Mock(return_value=SimpleNamespace(stdout=json.dumps({"models": [
            {"slug": "candidate", "visibility": "list", "supported_in_api": True},
            {"slug": "hidden", "visibility": "hide", "supported_in_api": True},
            {"slug": "unavailable", "visibility": "list", "supported_in_api": False},
        ]}), stderr=""))
        self.assertEqual(codex_catalog(runner, auth_mode="api"), [{"id": "candidate"}])
        runner.assert_called_once_with(["codex", "debug", "models"],
                                       capture_output=True, text=True, check=True, timeout=60)
        runner.return_value.stderr = "WARNING: could not create PATH aliases: Read-only file system (os error 30)"
        self.assertEqual(codex_catalog(runner, auth_mode="api"), [{"id": "candidate"}])

    def test_codex_refresh_failure_invalid_payload_and_timeout_stop(self):
        for stdout, stderr in (("{}", "refresh failed"), ("not-json", ""),
                               ('{"models":{}}', ""), ('{"models":[{}]}', "")):
            with self.subTest(stdout=stdout), self.assertRaises(ValueError):
                codex_catalog(Mock(return_value=SimpleNamespace(stdout=stdout, stderr=stderr)), auth_mode="api")
        with self.assertRaises(subprocess.TimeoutExpired):
            codex_catalog(Mock(side_effect=subprocess.TimeoutExpired("codex", 60)), auth_mode="api")

    def catalog(self, **updates):
        payload = {"surface": "cli", "source": "sdk.listModels",
                   "observed_at": datetime.now(timezone.utc).isoformat(),
                   "models": [{"id": "candidate"}, {"id": "disabled", "policy": {"state": "disabled"}},
                              {"id": "unavailable", "available": False}]}
        payload.update(updates)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "catalog.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_copilot_filters_policy_and_accepts_manual_same_surface(self):
        models, _ = copilot_catalog(self.catalog(), "cli")
        self.assertEqual(models, [{"id": "candidate"}])
        manual, evidence = copilot_catalog(self.catalog(source="/model", manual_reason="SDK unavailable"), "cli")
        self.assertEqual(manual, models)
        self.assertEqual(evidence["manual_reason"], "SDK unavailable")

    def test_surface_source_stale_future_and_malformed_availability_stop(self):
        now = datetime.now(timezone.utc)
        for updates in ({"surface": "ide"}, {"source": "vscode.lm.selectChatModels"},
                        {"source": "/model"}, {"source": "/model", "manual_reason": "  "},
                        {"source": "website"}, {"observed_at": (now - timedelta(hours=1)).isoformat()},
                        {"observed_at": (now + timedelta(hours=1)).isoformat()},
                        {"models": [{"id": "candidate", "policy": None}]},
                        {"models": [{"id": "candidate", "policy": {"state": ["disabled"]}}]},
                        {"models": [{"id": "candidate", "available": "false"}]}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                copilot_catalog(self.catalog(**updates), "cli")
        self.assertEqual(copilot_catalog(self.catalog(surface="ide", source="vscode.lm.selectChatModels"),
                                         "ide")[0], [{"id": "candidate"}])
