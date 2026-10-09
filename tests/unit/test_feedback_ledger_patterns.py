"""回帰テスト: ledger ID の参照欄は canonical pattern を使う。"""

import json
import unittest
from pathlib import Path

from feedback_ledger.schema import LEDGER_ID_RE, LEDGER_SPEC, PROPOSAL_SPEC, TRIAGE_SPEC

REPO_ROOT = Path(__file__).resolve().parents[2]


class LedgerReferencePatternTests(unittest.TestCase):
    def _schema(self, name):
        path = REPO_ROOT / ".ai/schema" / name
        return json.loads(path.read_text(encoding="utf-8"))

    def test_ledger_reference_patterns_match_id_acceptance(self):
        proposal = self._schema("feedback-proposal-v1.json")["properties"]
        ledger = self._schema("feedback-ledger-v1.json")["properties"]
        triage = self._schema("feedback-triage-v1.json")
        outcome = triage["$defs"]["outcome"]["properties"]
        id_pattern = ledger["id"]["pattern"]
        optional_pattern = f"^(?:|{id_pattern[1:-1]})$"
        references = (
            proposal["derived_from"]["items"]["pattern"],
            triage["properties"]["reviewed"]["items"]["pattern"],
            outcome["entry"]["pattern"],
        )
        self.assertTrue(all(pattern == id_pattern for pattern in references))
        self.assertEqual(ledger["supersedes"]["pattern"], optional_pattern)
        self.assertEqual(outcome["merged_into"]["pattern"], optional_pattern)
        fields = (
            PROPOSAL_SPEC.field_map()["derived_from"][1],
            TRIAGE_SPEC.field_map()["reviewed"][1],
            TRIAGE_SPEC.field_map()["outcomes.entry"][1],
            TRIAGE_SPEC.field_map()["outcomes.merged_into"][1],
        )
        valid = "FBK-20260901-adr-.-&-𠮟"
        invalid = "FBK-20260901-bad\u3000slug"
        self.assertTrue(all(field.pattern is LEDGER_ID_RE for field in fields))
        for field in fields:
            with self.subTest(field=field):
                self.assertIsNotNone(field.pattern.fullmatch(valid))
                self.assertIsNone(field.pattern.fullmatch(invalid))
        for pattern in (id_pattern, *references, optional_pattern):
            with self.subTest(pattern=pattern):
                self.assertRegex(valid, pattern)
                self.assertNotRegex(invalid, pattern)
        self.assertRegex("", optional_pattern)
