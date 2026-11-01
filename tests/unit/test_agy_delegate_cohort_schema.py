"""closed schema、存在区別、UTC寿命、全観測とaccount宣言の異常系。"""

import copy
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from agy_delegate.cohort_schema import canonical_proof_bytes, validate_proof
from tests.unit.test_agy_delegate_cohort_fixtures import NOW, fake_proof


class CohortSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.proof = fake_proof(Path(self.temporary.name))

    def test_closed_schema_rejects_missing_unknown_and_wrong_types_at_every_level(self):
        for path in [(), ("binding",), ("files",), ("files", "global"),
                     ("observations",), ("account_scope",)]:
            for action in ["extra", "missing", "type"]:
                with self.subTest(path=path, action=action):
                    data = copy.deepcopy(self.proof)
                    target = data
                    for key in path:
                        target = target[key]
                    if action == "extra":
                        target["raw_settings"] = "forbidden"
                    elif action == "missing":
                        del target[next(iter(target))]
                    elif path:
                        parent = data
                        for key in path[:-1]:
                            parent = parent[key]
                        parent[path[-1]] = []
                    else:
                        data = []
                    with self.assertRaises(ValueError):
                        validate_proof(data, now=NOW)

    def test_all_hashes_enums_bools_and_account_declarations_are_exact(self):
        variants = [("protocol", True), ("generator_source_sha256", "A" * 64)]
        for key, value in variants:
            data = copy.deepcopy(self.proof)
            data[key] = value
            with self.assertRaises(ValueError):
                validate_proof(data, now=NOW)
        for group in ["binding", "observations", "account_scope"]:
            for key in self.proof[group]:
                data = copy.deepcopy(self.proof)
                data[group][key] = 1 if group == "observations" else "unsupported"
                with self.subTest(group=group, key=key), self.assertRaises(ValueError):
                    validate_proof(data, now=NOW)

    def test_file_absence_is_distinct_and_global_must_exist(self):
        for group, field, value in [("global", "exists", False), ("project", "sha256", "a" * 64),
                                    ("global", "acl_sha256", None), ("shared", "exists", 0)]:
            data = copy.deepcopy(self.proof)
            data["files"][group][field] = value
            with self.assertRaises(ValueError):
                validate_proof(data, now=NOW)

    def test_lifetime_is_utc_not_future_and_at_most_24_hours(self):
        for now in [NOW - timedelta(seconds=1), NOW + timedelta(hours=24), NOW.replace(tzinfo=None)]:
            with self.assertRaises(ValueError):
                validate_proof(self.proof, now=now)
        for stamp in [(NOW + timedelta(hours=24, seconds=1)).isoformat(),
                      NOW.isoformat(), "2026-10-28T03:00:00+02:00", "2026-02-30T01:00:00Z"]:
            data = copy.deepcopy(self.proof)
            data["expires_utc"] = stamp
            with self.assertRaises(ValueError):
                validate_proof(data, now=NOW)

    def test_canonical_bytes_ignore_object_insertion_order(self):
        self.assertEqual(canonical_proof_bytes(self.proof, now=NOW), canonical_proof_bytes(
            dict(reversed(list(self.proof.items()))), now=NOW))
        self.assertEqual(validate_proof(self.proof, now=NOW), self.proof)

    def test_maximum_year_is_rejected_with_fixed_value_error_without_overflow(self):
        data = copy.deepcopy(self.proof)
        data["created_utc"] = "9999-12-31T00:00:00Z"
        data["expires_utc"] = "9999-12-31T23:00:00Z"
        with self.assertRaisesRegex(ValueError, "cohort_expired_or_future"):
            validate_proof(data, now=NOW)
        data["created_utc"] = "0001-01-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "cohort_lifetime_invalid"):
            validate_proof(data, now=NOW)
