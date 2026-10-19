"""Real migration provenance, rendering, and narrative lint regressions (#537)."""

import copy
import hashlib
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

from feedback_ledger.model import normalize_document
from feedback_ledger.render import render_ledger
from feedback_ledger.schema import LEDGER_SPEC
from feedback_ledger.store import load_store

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "audit/2026-09-21-pipeline-redesign"


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        self.ids.extend(value for key, value in attrs if key == "id")


class RealPolicyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.store = load_store(ROOT)
        self.manifest = json.loads((AUDIT / "migration.json").read_text())

    def test_original_67_items_and_all_nondecision_sections_are_preserved(self):
        original = (AUDIT / "history.md").read_text().split("\n\n", 1)[1]
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
                         self.manifest["source_sha256"])
        old_ids = re.findall(r'<a id="(fbk-[^"]+)"></a>', original)
        self.assertEqual(len(old_ids), 67)
        self.assertEqual(set(old_ids), {row["old_anchor"] for row in self.manifest["items"]})
        for row in self.manifest["items"]:
            document = self.store.by_id("ledger", row["entry_id"])
            self.assertIsNotNone(document)
            self.assertEqual(document.data["occurred_at"].isoformat(), row["judgment_date"])
            if row["representation"] == "decision-narrative":
                self.assertIn(row["old_id"], document.data["narrative"]["background"])
                self.assertIsNone(self.store.by_id("ledger", row["old_id"]))

    def test_readme_matches_render_and_all_old_anchors_resolve(self):
        rendered = render_ledger(self.store)
        self.assertEqual((AUDIT / "README.md").read_text(), rendered)
        parser = Anchors()
        parser.feed(rendered)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        for row in self.manifest["items"]:
            self.assertIn(row["old_anchor"], parser.ids)
        for fragment in re.findall(r'\]\(#([^)]*)\)', rendered):
            self.assertIn(unquote(fragment), parser.ids)
        self.assertLess(rendered.index("## 生存決定一覧"), rendered.index("## 旧参照の移行先"))
        self.assertIn("[移行前の原文・実測・未決事項（史料）](history.md)", rendered)

    def test_actual_verbatim_exceptions_do_not_permit_additional_inference(self):
        exceptions = json.loads((ROOT / "feedback_ledger/migration_allowlist.json").read_text())
        for exception in exceptions:
            data = copy.deepcopy(self.store.by_id("ledger", exception["document_id"]).data)
            _, clean = normalize_document(LEDGER_SPEC, data, "real-entry")
            self.assertFalse([item for item in clean if item.rule in ("L4", "L5")])
            data["narrative"]["owner_verbatim"] += "おそらく、この意図は推測できる。\n"
            _, rejected = normalize_document(LEDGER_SPEC, data, "real-entry")
            self.assertTrue(any(item.rule == "L4" for item in rejected))
            data["narrative"]["owner_verbatim"] = exception["value"]
            data["narrative"]["inferred_reason"] = "推測：オーナーはそうと明言した。\n"
            _, rejected = normalize_document(LEDGER_SPEC, data, "real-entry")
            self.assertTrue(any(item.rule == "L5" for item in rejected))

    def test_policy_sources_have_no_fabricated_review_association(self):
        for row in self.manifest["items"]:
            data = self.store.by_id("ledger", row["entry_id"]).data
            self.assertEqual(data["schema"], "feedback-ledger/v1.3")
            self.assertLessEqual(len(data["topic"]), 30)
            for source in data["source"]:
                self.assertEqual(source, {"issue": 537, "pr": 0, "round": 0, "finding_ids": []})
