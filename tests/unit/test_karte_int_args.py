"""``karte.int_args``：整数は ASCII 数字だけを受け、それ以外は呼び出し側の拒否例外に収める。"""

import unittest

from karte import int_args
from karte.errors import KarteUsageError
from karte.model import KarteFormatError
from tests.unit.karte_support import AT_CONVERSION_LIMIT, HUGE

NON_ASCII_DIGITS = ("²", "٣", "①")  # str.isdigit() は True だが int() できない


class TestAsciiIntOrNone(unittest.TestCase):
    def test_accepts_only_ascii_digits_within_the_conversion_limit(self):
        self.assertEqual(12, int_args.ascii_int_or_none("12"))
        self.assertEqual(0, int_args.ascii_int_or_none(0))
        for bad in (*NON_ASCII_DIGITS, "１２", "", "-1", "1.5", "5\n", HUGE):
            with self.subTest(bad=bad[:10]):
                self.assertIsNone(int_args.ascii_int_or_none(bad))

    def test_digit_limit_leaves_room_for_plus_one_to_stay_convertible(self):
        longest = "9" * int_args.MAX_DIGITS
        self.assertEqual(int(longest), int_args.ascii_int_or_none(longest))
        self.assertIsNone(int_args.ascii_int_or_none(longest + "9"))
        self.assertIsNone(int_args.ascii_int_or_none(int(longest) + 1))  # int のまま渡されても同じ
        self.assertTrue(str(int(longest) + 1))  # 受理される最大値の +1 は str() できる
        self.assertLess(int_args.MAX_DIGITS, 4300)

    def test_the_conversion_limit_itself_is_refused(self):
        """4300 桁ちょうどは int() を通るが、+1 した値の str() が ValueError になる（PR #696 第5回 R5-01）。"""
        self.assertEqual(4300, len(str(int(AT_CONVERSION_LIMIT))))
        self.assertIsNone(int_args.ascii_int_or_none(AT_CONVERSION_LIMIT))


class TestParseInt(unittest.TestCase):
    def test_accepts_ascii_digits_at_or_above_the_minimum(self):
        self.assertEqual(3, int_args.parse_int("3", "round"))
        self.assertEqual(0, int_args.parse_int(0, "round", minimum=0))

    def test_rejects_below_minimum_non_numbers_non_ascii_and_huge_digits(self):
        for value in ("0", "-1", "abc", "", "1.5", None, *NON_ASCII_DIGITS, HUGE, AT_CONVERSION_LIMIT):
            with self.subTest(value=str(value)[:10]), self.assertRaises(KarteUsageError):
                int_args.parse_int(value, "round")

    def test_non_ascii_digits_are_refused_even_when_zero_is_allowed(self):
        for value in NON_ASCII_DIGITS:
            with self.subTest(value=value), self.assertRaises(KarteUsageError):
                int_args.parse_int(value, "round", minimum=0)

    def test_error_message_is_truncated(self):
        with self.assertRaises(KarteUsageError) as caught:
            int_args.parse_int(HUGE, "round")
        self.assertLess(len(str(caught.exception)), 200)


class TestCallerSuppliedRefusal(unittest.TestCase):
    def test_require_ascii_int_raises_the_callers_exception(self):
        class Boom(Exception):
            pass

        with self.assertRaises(Boom):
            int_args.require_ascii_int(HUGE, Boom("x"))
        self.assertEqual(5, int_args.require_ascii_int("5", Boom("x")))

    def test_matched_int_names_what_was_too_long_without_a_stray_space(self):
        with self.assertRaises(KarteFormatError) as caught:
            int_args.matched_int(HUGE, KarteFormatError, "Result 見出しの番号")
        self.assertTrue(str(caught.exception).startswith("Result 見出しの番号の桁数が多すぎる"))
        self.assertLess(len(str(caught.exception)), 200)


if __name__ == "__main__":
    unittest.main()
