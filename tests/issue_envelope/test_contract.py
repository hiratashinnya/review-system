"""UT-TC: envelope境界の型・producer・鮮度・AC拒否。"""
import unittest
from issue_envelope.handoff import BINDINGS, validate_handoff
from issue_envelope.model import normalize
from .fixtures import artifact


class EnvelopeContractTests(unittest.TestCase):
    def test_all_producers_roundtrip(self):
        for kind in ("InvestigationReport", "VerificationDesign", "ChangePlan", "TestDesign"):
            with self.subTest(kind=kind):
                self.assertEqual(normalize(artifact(kind))["artifact_type"], kind)

    def test_wrong_producer_and_phase_are_rejected(self):
        for key, value in (("producer", "pr-reviewer"), ("phase", "1a"),
                           ("schema_version", 2), ("id", "VD-3710")):
            raw = artifact()
            raw[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                normalize(raw)

    def test_handoff_binds_every_expected_field(self):
        raw = artifact()
        expected = {key: raw[key] for key in BINDINGS}
        self.assertEqual(validate_handoff(raw, expected)["id"], raw["id"])
        for key in BINDINGS:
            bad = dict(expected, **{key: "stale"})
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_handoff(raw, bad)
        with self.assertRaises(ValueError):
            validate_handoff(raw, {})

    def test_stop_findings_and_owner_decisions_fail_closed(self):
        for key, value in (("unresolved_findings", ["FND-1"]),
                           ("unresolved_owner_decisions", ["Q-1"]), ("status", "stop")):
            raw = artifact()
            raw[key] = value
            if key == "status":
                raw["stop_reason"] = "owner回答待ち"
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_handoff(raw, {k: raw[k] for k in BINDINGS})

    def test_work_units_cover_approved_ac_exactly(self):
        raw = artifact("ChangePlan")
        expected = {key: raw[key] for key in BINDINGS}
        with self.assertRaises(ValueError):
            validate_handoff(raw, expected)
        expected["ac_refs"] = ["AC-1"]
        validate_handoff(raw, expected)
        expected["ac_refs"].append("AC-2")
        with self.assertRaises(ValueError):
            validate_handoff(raw, expected)

    def test_root_requires_system_design_and_cases(self):
        for key in ("st_td", "st_tc"):
            raw = artifact()
            raw[key] = []
            with self.subTest(key=key), self.assertRaises(ValueError):
                normalize(raw)
