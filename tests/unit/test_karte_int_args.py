"""``karte.int_args.parse_int``：整数引数は ASCII 数字だけを受け、それ以外は fail-close に収める。"""

import unittest

from karte import int_args
from karte.errors import KarteUsageError

NON_ASCII_DIGITS = ("²", "٣", "①")  # str.isdigit() は True だが int() できない


class TestParseInt(unittest.TestCase):
    def test_accepts_ascii_digits_at_or_above_the_minimum(self):
        self.assertEqual(3, int_args.parse_int("3", "round"))
        self.assertEqual(0, int_args.parse_int(0, "round", minimum=0))

    def test_rejects_below_minimum_and_non_numbers(self):
        for value in ("0", "-1", "abc", "", "1.5", None):
            with self.subTest(value=value):
                with self.assertRaises(KarteUsageError):
                    int_args.parse_int(value, "round")

    def test_non_ascii_digits_raise_usage_error_not_value_error(self):
        for value in NON_ASCII_DIGITS:
            with self.subTest(value=value):
                with self.assertRaises(KarteUsageError):
                    int_args.parse_int(value, "round", minimum=0)


class TestHugeDigitStrings(unittest.TestCase):
    """桁数が多すぎる数字列は int() の変換上限で ValueError になる。fail-close に収める（L3）。"""

    HUGE = "9" * 6000

    def test_parse_int_raises_usage_error_for_huge_digit_strings(self):
        with self.assertRaises(KarteUsageError):
            int_args.parse_int(self.HUGE, "round")

    def test_error_message_is_truncated(self):
        with self.assertRaises(KarteUsageError) as caught:
            int_args.parse_int(self.HUGE, "round")
        self.assertLess(len(str(caught.exception)), 200)


if __name__ == "__main__":
    unittest.main()
