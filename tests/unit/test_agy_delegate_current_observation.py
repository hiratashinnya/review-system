"""現版の秘匿済みschema観測を旧fixtureと区別する。"""

import json
import unittest
from pathlib import Path

from agy_delegate.output_contract import CONTRACT_VERSION, REQUIRED, contract_reasons


class CurrentObservationTests(unittest.TestCase):
    def test_measured_success_schema_and_typed_usage_do_not_prove_denial(self):
        path = Path(__file__).resolve().parents[1] / "fixtures/agy_delegate/1.4.8/success-shape.json"
        observed = json.loads(path.read_text())
        self.assertEqual(observed["version"], CONTRACT_VERSION)
        self.assertEqual(set(observed["schema"]["fields"]), REQUIRED)
        self.assertEqual(observed["schema"]["fields"]["status"]["known_enum"], "SUCCESS")
        self.assertTrue(observed["binary_unchanged"])
        self.assertTrue(observed["settings_restored"])
        self.assertTrue(observed["corpus_unchanged"])
        self.assertFalse(observed["write_denial_verified"])
        synthesized = {"status": "SUCCESS", "conversation_id": "synthetic-redacted-id",
                       "response": "synthetic-response-not-original", "duration_seconds": 0.5,
                       "num_turns": observed["num_turns"], "usage": observed["usage"]}
        self.assertEqual(contract_reasons(synthesized), [])

