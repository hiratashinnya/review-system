"""全snapshot項目の未知/欠落/型/差異と理由の非漏洩を検査する。"""

import copy
from unittest.mock import patch

from agy_delegate.cohort_current_binding import compare_current_proof
from agy_delegate.cohort_schema import validated_files
from tests.unit.test_agy_delegate_cohort_fixtures import CohortStoreFixture


class CohortCurrentFilesTests(CohortStoreFixture):
    def setUp(self):
        super().setUp()
        for name in ["project", "shared"]:
            self.proof["files"][name] = self.proof["files"]["global"].copy()

    def compare(self, files):
        return compare_current_proof(
            self.proof, current_binding=self.proof["binding"], current_files=files,
            generator_sha256=self.proof["generator_source_sha256"])

    def test_all_file_groups_and_members_reject_missing_unknown_and_bad_types(self):
        for group in self.proof["files"]:
            without_group = copy.deepcopy(self.proof["files"])
            del without_group[group]
            self.assertEqual(self.compare(without_group), ["cohort_current_files_invalid"])
            for field in self.proof["files"][group]:
                for action in ["missing", "type", "changed"]:
                    current = copy.deepcopy(self.proof["files"])
                    if action == "missing":
                        del current[group][field]
                    else:
                        current[group][field] = "secret" if action == "type" else "0" * 64
                    reason = ("cohort_files_mismatch" if action == "changed" and
                              field != "exists" else "cohort_current_files_invalid")
                    with self.subTest(group=group, field=field, action=action):
                        self.assertEqual(self.compare(current), [reason])
            current = copy.deepcopy(self.proof["files"])
            current[group]["unknown"] = "secret"
            self.assertEqual(self.compare(current), ["cohort_current_files_invalid"])
        for current in [False, [], self.proof["files"] | {"admin": {}}]:
            self.assertEqual(self.compare(current), ["cohort_current_files_invalid"])

    def test_presence_change_is_distinct_from_missing_fields(self):
        absent = {"exists": False, "sha256": None, "acl_sha256": None, "owner_sha256": None}
        for group in ["project", "shared"]:
            current = copy.deepcopy(self.proof["files"])
            current[group] = absent.copy()
            self.assertEqual(self.compare(current), ["cohort_files_mismatch"])
        current = copy.deepcopy(self.proof["files"])
        current["global"] = absent
        self.assertEqual(self.compare(current), ["cohort_current_files_invalid"])
        self.assertEqual(validated_files(self.proof["files"]), self.proof["files"])

    def test_multiple_mismatches_keep_all_reasons_without_raw_hashes_or_children(self):
        current_files = copy.deepcopy(self.proof["files"])
        current_files["global"]["sha256"] = "0" * 64
        binding = self.proof["binding"] | {"os_sha256": "0" * 64}
        with patch("subprocess.run") as child:
            reasons = compare_current_proof(self.proof, current_binding=binding,
                                           current_files=current_files, generator_sha256="0" * 64)
        self.assertEqual(reasons, ["cohort_binding_mismatch", "cohort_files_mismatch",
                                   "cohort_generator_mismatch"])
        self.assertNotIn("0" * 64, repr(reasons))
        child.assert_not_called()
