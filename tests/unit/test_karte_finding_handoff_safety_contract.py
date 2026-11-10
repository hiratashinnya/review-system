"""申し送りの計数・レポート・ロック境界。"""
import unittest
from dataclasses import replace

from karte import exit_codes, model, paths
from karte.finding_handoff_exemption import is_stall_exempt
from karte.stall_detection import stalled_ids
from tests.unit.karte_support import RootedCase
from tests.unit.test_karte_finding_handoff_ingest import FIELDS
from tests.unit.test_karte_finding_handoff_predicate import verified_item
from tests.unit.test_karte_finding_handoff_verb_support import VerbCase


class HandoffCountingContractTest(unittest.TestCase):
    def test_verified_state_and_destination_required(self):
        item = verified_item()
        self.assertTrue(is_stall_exempt(item))
        invalid = replace(item, handoff=replace(item.handoff, handoff_state="invalid"))
        changed = replace(item, deferred_to="#10")
        self.assertEqual([item.id], stalled_ids(model.Karte(7, [invalid])))
        self.assertEqual([item.id], stalled_ids(model.Karte(7, [changed])))


class HandoffReportContractTest(RootedCase):
    def test_report_cannot_create_handoff(self):
        code, _, _ = self.ingest(1, ("new", {**FIELDS, "handoff_state": "verified"}))
        self.assertEqual(exit_codes.EXIT_ERROR, code)
        self.assertFalse(paths.karte_path(7, self.root).exists())


class HandoffLockContractTest(VerbCase):
    def test_post_and_recheck_observe_without_writer_lock(self):
        # VerbCase.run_process asserts the writer lock is not held for each call.
        self.assertEqual(0, self.post()[0])
        self.assertEqual(0, self.call("handoff-recheck")[0])
