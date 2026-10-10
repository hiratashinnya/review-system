"""Regression tests for Unicode ledger IDs and normalized collisions."""

import io
import importlib.util
import json
import re
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from feedback_ledger import slugify_ref
from feedback_ledger import paths as paths_module
from feedback_ledger.cli import main
from feedback_ledger.model import check_document_identity
from feedback_ledger.schema import LEDGER_ID_RE, LEDGER_SPEC
from feedback_ledger.schema_values import has_unsafe_ledger_slug_character
from feedback_ledger.store import load_store
from test_feedback_ledger import FeedbackLedgerTestCase, ledger_data


class LedgerIdentityReviewTests(FeedbackLedgerTestCase):
    def test_reference_hostile_characters_are_rejected_by_id_pattern(self):
        spec = importlib.util.spec_from_file_location("slugify_ref_test", slugify_ref.SLUGIFY_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for character in module._HOSTILE:
            with self.subTest(character=character):
                value = f"FBK-20260901-a{character}b"
                self.assertIsNone(LEDGER_ID_RE.fullmatch(value))

    def test_punctuation_and_supplementary_kanji_are_accepted(self):
        topic = "ADR . & 𠮟"
        document_id = f"FBK-20260901-{slugify_ref.slugify_topic(topic)}"
        schema_path = Path(__file__).resolve().parents[2] / ".ai/schema/feedback-ledger-v1.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertIsNotNone(LEDGER_ID_RE.fullmatch(document_id))
        self.assertRegex(document_id, re.compile(schema["properties"]["id"]["pattern"]))
        self.assertRegex(document_id, re.compile(schema["properties"]["supersedes"]["pattern"]))
        draft = self.write_draft(LEDGER_SPEC, ledger_data(topic=topic, id=document_id))
        self.assertEqual(self.run_cli("new-entry", "--from", draft)[0], 0)

    def test_python_validation_rejects_unicode_other_categories(self):
        for character in ("\u0001", "\u200d", "\ud800", "\ue000", "\u0378"):
            with self.subTest(category=__import__("unicodedata").category(character)):
                topic = "valid topic"
                document_id = f"FBK-20260901-valid{character}slug"
                self.assertTrue(has_unsafe_ledger_slug_character(document_id))
                findings = check_document_identity(
                    LEDGER_SPEC, ledger_data(topic=topic, id=document_id), "draft.toml"
                )
                self.assertTrue(any(item.locus == "draft.toml::id" for item in findings))

    def test_concurrent_new_entry_serializes_collision_check(self):
        first_topic, second_topic = "AI", "ＡＩ"
        first_id = f"FBK-20260901-{slugify_ref.slugify_topic(first_topic)}"
        second_id = f"FBK-20260901-{slugify_ref.slugify_topic(second_topic)}"
        drafts = [
            self.write_draft(LEDGER_SPEC, ledger_data(topic=topic, id=document_id))
            for topic, document_id in ((first_topic, first_id), (second_topic, second_id))
        ]
        barrier = Barrier(2)
        original_lock = paths_module.writer_lock

        @contextmanager
        def synchronized_lock(root):
            barrier.wait(timeout=5)
            with original_lock(root):
                yield

        def submit(draft):
            return main(["--root", str(self.root), "new-entry", "--from", draft])

        stderr = io.StringIO()
        with patch.object(paths_module, "writer_lock", synchronized_lock):
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    codes = list(executor.map(submit, drafts))
        self.assertCountEqual(codes, [0, 4])
        self.assertEqual(len(load_store(self.root).of(LEDGER_SPEC.kind)), 1)
        self.assertIn("NFKC+casefold", stderr.getvalue())

    def test_check_reports_nfkc_casefold_collision(self):
        for topic in ("AI", "ＡＩ"):
            document_id = f"FBK-20260901-{slugify_ref.slugify_topic(topic)}"
            self.place(LEDGER_SPEC, ledger_data(topic=topic, id=document_id))
        code, output = self.run_cli("check")
        self.assertEqual(code, 4)
        self.assertIn("NFKC+casefold", output)


if __name__ == "__main__":
    unittest.main()
