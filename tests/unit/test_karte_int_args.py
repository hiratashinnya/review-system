"""``karte.int_args``：整数は ASCII 数字だけを受け、それ以外は呼び出し側の拒否例外に収める。"""

import unittest

from karte import int_args
from karte.errors import KarteUsageError
from karte.model import KarteFormatError

NON_ASCII_DIGITS = ("²", "٣", "①")  # str.isdigit() は True だが int() できない
HUGE = "9" * 6000  # int の変換上限（4300 桁）を超える


class TestAsciiIntOrNone(unittest.TestCase):
    def test_accepts_only_ascii_digits_within_the_conversion_limit(self):
        self.assertEqual(12, int_args.ascii_int_or_none("12"))
        self.assertEqual(0, int_args.ascii_int_or_none(0))
        for bad in (*NON_ASCII_DIGITS, "１２", "", "-1", "1.5", "5\n", HUGE):
            with self.subTest(bad=bad[:10]):
                self.assertIsNone(int_args.ascii_int_or_none(bad))


class TestParseInt(unittest.TestCase):
    def test_accepts_ascii_digits_at_or_above_the_minimum(self):
        self.assertEqual(3, int_args.parse_int("3", "round"))
        self.assertEqual(0, int_args.parse_int(0, "round", minimum=0))

    def test_rejects_below_minimum_non_numbers_non_ascii_and_huge_digits(self):
        for value in ("0", "-1", "abc", "", "1.5", None, *NON_ASCII_DIGITS, HUGE):
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
