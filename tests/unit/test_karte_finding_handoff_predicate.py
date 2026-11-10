"""申し送り先・無進捗除外・台帳互換の試験。"""

import unittest
from dataclasses import replace
from unittest import mock

from karte import model
from karte.finding_handoff_exemption import is_stall_exempt
from karte.finding_handoff_hash import content_hash
from karte.finding_handoff_record import HandoffRecord
from karte.finding_handoff_target import normalize_target
from karte.render_finding_lines import render_finding_lines
from karte.status_payload import status_payload
from karte.status_text import status_lines
from karte.stall_detection import stalled_ids


def verified_item(number=1):
    item = model.Finding(id=f"F-7-{number:02d}", harm="none", harm_detail="実害なし", severity="minor",
                         summary="要約", locus=["a.py"], expected="期待", evidence="根拠", recheck="確認",
                         disposition="deferred", deferred_to="#9", rounds=list(range(1, 12)))
    item.handoff = HandoffRecord("Owner/Repo#9", "https://example.test/comment", content_hash(
        item.id, item.harm, item.summary, item.locus, item.expected), "2026-01-01T00:00:00Z", "verified")
    return item


class HandoffPredicateTest(unittest.TestCase):
    def test_targets(self):
        for value in ("#9", "9", "https://github.com/owner/REPO/issues/9"):
            self.assertEqual("Owner/Repo#9", normalize_target(value, "Owner/Repo"))
        for value in ("https://github.com/other/repo/issues/9", "https://other/Owner/Repo/issues/9",
                      "https://github.com/Owner/Repo/pull/9", "#0", "bad"):
            self.assertIsNone(normalize_target(value, "Owner/Repo"))

    def test_predicate_fail_close(self):
        item = verified_item()
        self.assertTrue(is_stall_exempt(item))
        changes = (("status", "resolved"), ("harm", "real"), ("disposition", "waived"),
                   ("disposition", ""), ("disposition", "fix-here"), ("deferred_to", "#10"),
                   ("deferred_to", "https://github.com/else/repo/issues/9"), ("id", "F-7-02"),
                   ("handoff", None))
        for field, value in changes:
            with self.subTest(field=field, value=value):
                self.assertFalse(is_stall_exempt(replace(item, **{field: value})))
        for field, value in (("handoff_state", "invalid"), ("handoff_state", ""),
                             ("handoff_content_hash", "sha256:" + "0" * 64)):
            self.assertFalse(is_stall_exempt(replace(item, handoff=replace(item.handoff, **{field: value}))))

    def test_ledger_and_legacy(self):
        item = verified_item()
        ledger = model.Karte(issue=7, findings=[item])
        text = model.dumps(ledger)
        self.assertEqual(ledger, model.parse(model.dumps(model.parse(text))))
        with mock.patch("karte.block_records.record_from_block", return_value=None):
            old = model.dumps(model.parse(text))
        self.assertNotIn("handoff_", old)
        old_item = model.parse(old).findings[0]
        self.assertFalse(is_stall_exempt(old_item))
        self.assertEqual(old, model.dumps(model.parse(old)))
        typo = text.replace("handoff_state:", "handoff_statte:")
        self.assertFalse(is_stall_exempt(model.parse(typo).findings[0]))
        self.assertEqual([item.id], stalled_ids(model.parse(typo)))

    def test_status_and_render_share_predicate(self):
        ledger = model.Karte(issue=7, findings=[verified_item(1), verified_item(2)])
        payload = status_payload(ledger)
        self.assertEqual("no-harm-only", payload["verdict"])
        self.assertEqual(["F-7-01", "F-7-02"], payload["handoff_exempt_findings"])
        self.assertFalse(payload["stalled_findings"] or payload["escalate"])
        self.assertNotIn("★無進捗", "\n".join(render_finding_lines(ledger)))
        self.assertIn("F-7-01, F-7-02", "\n".join(status_lines(7, "path", payload)))
        ledger.findings[0].handoff = replace(ledger.findings[0].handoff, handoff_state="invalid")
        ledger.findings[1].handoff = None
        payload = status_payload(ledger)
        self.assertNotIn("handoff_exempt_findings", payload)
        self.assertTrue(payload["escalate"])
        self.assertEqual(2, len(payload["stalled_findings"]))
        self.assertNotIn("検証済み申し送り", "\n".join(status_lines(7, "path", payload)))

    def test_existing_disposition_counting(self):
        base = verified_item()
        cases = (("real", "deferred", False), ("real", "waived", False),
                 ("none", "waived", True), ("none", "", True))
        for harm, disposition, stalled in cases:
            with self.subTest(harm=harm, disposition=disposition):
                item = replace(base, harm=harm, disposition=disposition)
                self.assertEqual([item.id] if stalled else [], stalled_ids(model.Karte(7, [item])))
