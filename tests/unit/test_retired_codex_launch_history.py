"""Ledger history boundary and actual runtime reintroduction probes (#537)."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from feedback_ledger.model import normalize_document
from feedback_ledger.schema import LEDGER_SPEC
from feedback_ledger.slugify_ref import slugify_topic
from feedback_ledger.store import canonical_text, load_store
from tests.unit import test_retired_codex_launch_stack as scanner


class RetiredCodexHistoryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.names = scanner.RETIRED_MODULE_AND_HOOK_NAMES
        self.probe = scanner.RetiredCodexLaunchStackTests(
            "test_retired_module_and_hook_names_do_not_reappear_in_active_tree")

    def scan(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        with patch.object(scanner, "ROOT", self.root), \
                patch.object(scanner, "_tracked_files", return_value=[relative]):
            self.probe.test_retired_module_and_hook_names_do_not_reappear_in_active_tree()

    def test_new_canonical_ledger_record_preserves_retired_names_as_history(self):
        original = load_store(scanner.ROOT).of("ledger")[0].data
        data = copy.deepcopy(original)
        data["schema"] = "feedback-ledger/v1.3"
        data["topic"] = "退役名の史料記録を保存する"
        data["id"] = f'FBK-{data["occurred_at"]:%Y%m%d}-{slugify_topic(data["topic"])}'
        data["narrative"]["background"] = "\n".join(self.names) + "\n"
        data, findings = normalize_document(LEDGER_SPEC, data, "synthetic-history")
        self.assertEqual(findings, [])
        relative = ".ai/feedback/ledger/" + data["id"] + ".toml"
        self.assertFalse(scanner._is_active(relative))
        self.scan(relative, canonical_text(LEDGER_SPEC, data))

    def test_runtime_and_config_names_remain_detectable_including_inside_ledger(self):
        paths = (
            f"issue_start/{self.names[0]}.py",
            f".codex/hooks/{self.names[-1]}.sh",
            "issue_start/managed-entrypoints-v2.json",
            ".ai/feedback/config.toml",
            ".ai/feedback/ledger/config.toml",
            ".ai/feedback/ledger/runtime.py",
            ".ai/feedback/ledger/runtime.sh",
            ".ai/feedback/ledger/nested/runtime.py",
            ".ai/feedback/ledger/nested/FBK-20260922-履歴.toml",
        )
        for relative in paths:
            with self.subTest(path=relative):
                self.assertTrue(scanner._is_active(relative))
                with self.assertRaises(AssertionError):
                    self.scan(relative, "\n".join(self.names))

    def test_existing_history_roots_remain_excluded(self):
        for prefix in scanner.HISTORY_ROOTS:
            relative = prefix + "retired-history.md"
            with self.subTest(path=relative):
                self.assertFalse(scanner._is_active(relative))
                self.scan(relative, "\n".join(self.names))
