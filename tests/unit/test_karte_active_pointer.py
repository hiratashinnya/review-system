"""``karte.active_pointer.read_active``：補完に使う（``required``）ときの拒否と、使わないときの縮退。

「まだ無い」（正常な初期状態）と「壊れている」は別物。``required`` の拒否は、利用者が次に
何をすればよいか（先に ``ingest-review`` を明示指定で実行する）を文言で示す。
"""

import unittest

from karte import active_pointer, exit_codes
from karte.errors import KarteUsageError
from tests.unit.karte_support import RootedCase

NEXT_STEP = "先に `ingest-review --issue N --round R` を明示指定で実行する"


class TestMissingPointer(RootedCase):
    prefix = "karte-ap-"

    def test_without_the_karte_directory_the_refusal_says_the_pointer_is_missing(self):
        with self.assertRaises(KarteUsageError) as caught:
            active_pointer.read_active(self.root, required=True)
        self.assertIn("進行ポインタが無い: ", str(caught.exception))
        self.assertIn("カルテ置き場が無い", str(caught.exception))  # 原因（置き場が未作成）を引き継ぐ

    def test_without_the_file_the_refusal_names_the_path_and_the_next_step(self):
        (self.root / "tmp" / "_karte").mkdir()
        with self.assertRaises(KarteUsageError) as caught:
            active_pointer.read_active(self.root, required=True)
        message = str(caught.exception)
        self.assertIn(str(self.root / "tmp" / "_karte" / "active.json"), message)
        self.assertIn("が無い", message)
        self.assertIn(NEXT_STEP, message)

    def test_it_degrades_to_an_empty_pointer_when_not_required(self):
        self.assertEqual({}, active_pointer.read_active(self.root))
        (self.root / "tmp" / "_karte").mkdir()
        self.assertEqual({}, active_pointer.read_active(self.root))

    def test_a_present_pointer_is_returned_whether_or_not_it_is_required(self):
        self.write_pointer('{"issue": 7, "round": 2}')
        for required in (False, True):
            with self.subTest(required=required):
                self.assertEqual(
                    {"issue": 7, "round": 2}, active_pointer.read_active(self.root, required=required)
                )


class TestCompletionWithoutAPointerTellsTheNextStep(RootedCase):
    prefix = "karte-ap2-"

    def test_verbs_that_complete_the_issue_refuse_and_say_what_to_run_first(self):
        for argv in (["status"], ["render"], ["check", "--round", "1"]):
            with self.subTest(argv=argv):
                code, _out, err = self.run_verb(argv)
                self.assertEqual(exit_codes.EXIT_ERROR, code, err)
                self.assertIn("進行ポインタ", err)

    def test_the_file_missing_case_reaches_the_user_with_the_next_step(self):
        (self.root / "tmp" / "_karte").mkdir()
        code, _out, err = self.run_verb(["status"])
        self.assertEqual(exit_codes.EXIT_ERROR, code, err)
        self.assertIn(NEXT_STEP, err)


if __name__ == "__main__":
    unittest.main()
