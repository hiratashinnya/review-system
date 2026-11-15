"""Issue #801: finding 0 件でも review round を失わないモデルの回帰テスト。"""

import unittest

from karte import model, karte_rounds
from karte.review_round_record import ReviewRound

DIGEST = "a" * 64


class ReviewRoundReceiptTest(unittest.TestCase):
    def test_receipt_survives_roundtrip_without_findings(self):
        karte = model.new_karte(801)
        karte.review_rounds.append(ReviewRound(1, DIGEST))
        serialized = model.dumps(karte)
        self.assertIn("## Review Rounds", serialized)
        self.assertIn("### Review Round 1", serialized)
        loaded = model.parse(serialized)
        self.assertEqual(loaded.review_rounds, [ReviewRound(1, DIGEST)])
        self.assertEqual(karte_rounds.last_round(loaded), 1)
        self.assertEqual(loaded.findings, [])

    def test_existing_karte_format_is_unchanged(self):
        serialized = model.dumps(model.new_karte(801))
        self.assertNotIn("Review Rounds", serialized)
        self.assertEqual(model.dumps(model.parse(serialized)), serialized)

    def test_rounds_are_sorted_and_latest_is_selected(self):
        karte = model.new_karte(801)
        karte.review_rounds.extend([ReviewRound(3, DIGEST), ReviewRound(1, DIGEST)])
        loaded = model.parse(model.dumps(karte))
        self.assertEqual([r.number for r in loaded.review_rounds], [1, 3])
        self.assertEqual(karte_rounds.last_round(loaded), 3)

    def test_duplicate_round_fails_closed(self):
        text = model.dumps(model.new_karte(801))
        body = "## Review Rounds\n\n### Review Round 1\ndigest: " + DIGEST + "\n"
        text = text.replace("## Attempts", body + "\n" + body + "\n## Attempts")
        with self.assertRaisesRegex(model.KarteFormatError, "重複"):
            model.parse(text)

    def test_bad_digest_and_unexpected_key_fail_closed(self):
        original = model.dumps(model.new_karte(801))
        for invalid in ("digest: xyz", "digest: " + DIGEST + "\nstatus: clean", "unknown: true"):
            text = original.replace("## Attempts", "## Review Rounds\n\n### Review Round 1\n" + invalid + "\n\n## Attempts")
            with self.subTest(invalid=invalid), self.assertRaises(model.KarteFormatError):
                model.parse(text)

    def test_invalid_title_fails_closed(self):
        original = model.dumps(model.new_karte(801))
        text = original.replace("## Attempts", "## Review Rounds\n\n### Review Round 0\ndigest: " + DIGEST + "\n\n## Attempts")
        with self.assertRaises(model.KarteFormatError):
            model.parse(text)


if __name__ == "__main__":
    unittest.main()
