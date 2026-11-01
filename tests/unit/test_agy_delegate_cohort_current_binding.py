"""全binding項目とgeneratorの型/欠落/差異を純粋比較する。"""

import copy
from unittest.mock import patch

from agy_delegate.cohort_current_binding import compare_current_proof
from agy_delegate.cohort_fields import BINDING_HASHES
from agy_delegate.cohort_schema import validated_binding
from tests.unit.test_agy_delegate_cohort_fixtures import CohortStoreFixture


class CohortCurrentBindingTests(CohortStoreFixture):
    def compare(self, *, proof=None, binding=None, generator=None):
        return compare_current_proof(
            self.proof if proof is None else proof,
            current_binding=self.proof["binding"] if binding is None else binding,
            current_files=self.proof["files"],
            generator_sha256=self.proof["generator_source_sha256"] if generator is None else generator)

    def test_matching_fields_have_no_reasons_and_no_children(self):
        with patch("subprocess.run") as run, patch("subprocess.Popen") as popen:
            self.assertEqual(self.compare(), [])
        run.assert_not_called()
        popen.assert_not_called()
        self.assertEqual(validated_binding(self.proof["binding"]), self.proof["binding"])

    def test_every_binding_member_rejects_missing_wrong_type_and_changes(self):
        original = self.proof["binding"]
        for key in original:
            for action in ["missing", "type", "changed"]:
                current = copy.deepcopy(original)
                if action == "missing":
                    del current[key]
                else:
                    current[key] = False if action == "type" else "0" * 64
                expected = ("cohort_binding_mismatch" if action == "changed" and
                            key in BINDING_HASHES else "cohort_current_binding_invalid")
                with self.subTest(key=key, action=action):
                    self.assertEqual(self.compare(binding=current), [expected])
        for current in [[], False, original | {"unknown": "secret"}]:
            self.assertEqual(self.compare(binding=current), ["cohort_current_binding_invalid"])

    def test_generator_type_format_and_mismatch_have_fixed_reasons(self):
        for value in [False, 1, [], "secret", "A" * 64]:
            self.assertEqual(self.compare(generator=value), ["cohort_current_generator_invalid"])
        self.assertEqual(self.compare(generator="0" * 64), ["cohort_generator_mismatch"])

    def test_unknown_missing_or_malformed_proof_never_exposes_original_values(self):
        for key in self.proof:
            invalid = copy.deepcopy(self.proof)
            del invalid[key]
            self.assertEqual(self.compare(proof=invalid), ["cohort_proof_invalid"])
        variants = [self.proof | {"secret-rule": "secret"}, [], False]
        invalid = copy.deepcopy(self.proof)
        invalid["observations"]["secret"] = "secret"
        variants.append(invalid)
        for invalid in variants:
            with patch("subprocess.run") as child:
                self.assertEqual(self.compare(proof=invalid), ["cohort_proof_invalid"])
            child.assert_not_called()

    def test_expiry_is_reader_responsibility_comparison_does_not_read_the_clock(self):
        self.proof["created_utc"] = "2000-01-01T00:00:00Z"
        self.proof["expires_utc"] = "2000-01-01T01:00:00Z"
        self.assertEqual(self.compare(), [])
