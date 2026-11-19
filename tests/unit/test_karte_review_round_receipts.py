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

    def test_accepted_ac_origin_roundtrip_and_malformed_ref_fails_closed(self):
        report_source = "tmp/_karte/issue-801-review-round-1.md"
        ac_source = "tmp/_karte/issue-801-ac-round-1-" + "b" * 64 + ".md"
        rec = ReviewRound(1, DIGEST, report_source, ac_source, "github.com", "owner/repo")
        karte = model.new_karte(801)
        karte.review_rounds.append(rec)
        rendered = model.dumps(karte)
        self.assertEqual(model.parse(rendered).review_rounds, [rec])
        for corrupt in (
            rendered.replace("ac_host: github.com\n", ""),
            rendered.replace("ac_host: github.com", "ac_host: bad..host"),
            rendered.replace("ac_source: " + ac_source, "ac_source: tmp/other.md"),
        ):
            with self.subTest(corrupt=corrupt), self.assertRaises(model.KarteFormatError):
                model.parse(corrupt)
        karte.review_rounds = [ReviewRound(1, DIGEST, report_source, ac_source)]
        self.assertEqual(model.parse(model.dumps(karte)).review_rounds, karte.review_rounds)

    def test_main_614_fields_and_801_roundtrip_without_loss(self):
        from karte.check_diagnosis import exemption_reason
        from karte.status_verdict import status_verdict

        entry = model.Finding(
            id="F-801-01", rounds=[1], harm="real", harm_detail="受入条件が未充足",
            disposition="fix-here", diagnosis_owner="main",
            override_ref="FBK-20261116-merge-compat",
            reachability_path="ユーザー操作→CLI→判定",
            threat_assumption="悪意のない誤操作・入力条件",
            summary="検証が残る", evidence="未測定", expected="検証完了",
            recheck="回帰テストを実施",
        )
        karte = model.new_karte(801)
        karte.findings.append(entry)
        karte.review_rounds.append(ReviewRound(1, DIGEST))
        rendered = model.dumps(karte)
        for field in ("diagnosis_owner: main", "override_ref:",
                      "reachability_path:", "threat_assumption:",
                      "## Review Rounds", "### Review Round 1"):
            self.assertIn(field, rendered)
        parsed = model.parse(rendered)
        restored = parsed.finding(entry.id)
        for field in ("diagnosis_owner", "override_ref",
                      "reachability_path", "threat_assumption"):
            self.assertEqual(getattr(restored, field), getattr(entry, field))
        self.assertEqual(parsed.review_rounds, [ReviewRound(1, DIGEST)])
        self.assertEqual(model.dumps(parsed), rendered)
        self.assertEqual("harmful-open", status_verdict(parsed)[-1])
        self.assertIn("主文脈", exemption_reason(restored, {}))
        # 旧カルテに新診断担当の行が無い場合は従来の fixer が既定。
        legacy = model.parse(rendered.replace("diagnosis_owner: main\n", ""))
        self.assertEqual(legacy.finding(entry.id).diagnosis_owner, "fixer")

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
