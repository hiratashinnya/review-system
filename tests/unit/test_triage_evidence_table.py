"""Issue #783 F-783-08: one per-phase evidence table drives context, assessment and schema."""

import json
from pathlib import Path
import unittest

from finding_triager.adapter import propose
from finding_triager.validator import validate_proposal
from triage_policy.evidence import (ARTIFACT_DIFF, CATEGORIES, CHANGE_SOURCE, PHASE_EVIDENCE,
                                    PULL_REQUEST_DIFF, required_categories)
from triage_policy.phases import PROPOSAL_PHASES
from tests.unit.triage_phase_support import propose_args

ARTIFACT_SCHEMA = json.loads((Path(__file__).resolve().parents[2] / ".ai/schema/finding-triage-v1.json")
                             .read_text(encoding="utf-8"))


def schema_evidence(phase):
    """Required and forbidden evidence keys the artifact schema demands for ``phase``."""
    node = ARTIFACT_SCHEMA["properties"]["proposals"]["items"]["properties"]["triager"]["properties"]["evidence"]
    required, forbidden = set(node["required"]), set()
    for rule in ARTIFACT_SCHEMA["allOf"]:
        chosen = rule["then"] if phase == rule["if"]["properties"]["phase"]["const"] else rule["else"]
        inner = chosen["properties"]["proposals"]["items"]["properties"]["triager"]["properties"]["evidence"]
        required |= set(inner.get("required", []))
        forbidden |= set(inner.get("not", {}).get("required", []))
    return required, forbidden, set(node["properties"])


class EvidenceTableTest(unittest.TestCase):
    def test_table_covers_exactly_the_proposal_phases(self):
        self.assertEqual(set(PHASE_EVIDENCE), set(PROPOSAL_PHASES))
        self.assertEqual(set(CHANGE_SOURCE), set(PROPOSAL_PHASES))

    def test_verification_design_has_no_design_category_and_others_keep_all_four(self):
        self.assertEqual(PHASE_EVIDENCE["verification_design"], ("ac", "vd_cp", "change"))
        for phase in PROPOSAL_PHASES[1:]:
            self.assertEqual(PHASE_EVIDENCE[phase], CATEGORIES)

    def test_change_means_pr_diff_only_for_implementation_reviews(self):
        for phase in PROPOSAL_PHASES:
            expected = PULL_REQUEST_DIFF if phase in ("review", "remediation_review") else ARTIFACT_DIFF
            self.assertEqual(CHANGE_SOURCE[phase], expected)

    def test_unknown_phase_has_no_categories(self):
        for phase in ("planning", "", None, ["review"], 7):
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                required_categories(phase)

    def test_artifact_schema_agrees_with_table(self):
        for phase in PROPOSAL_PHASES:
            required, forbidden, allowed = schema_evidence(phase)
            with self.subTest(phase=phase):
                self.assertEqual(required, set(PHASE_EVIDENCE[phase]))
                self.assertEqual(allowed - forbidden, set(PHASE_EVIDENCE[phase]))


class PerPhaseEvidenceTest(unittest.TestCase):
    def test_exact_categories_pass_and_artifact_carries_only_them(self):
        for phase in PROPOSAL_PHASES:
            args = propose_args(phase)
            artifact = propose(*args)
            with self.subTest(phase=phase):
                self.assertEqual(validate_proposal(artifact, *args), artifact)
                self.assertEqual(artifact["phase"], phase)
                self.assertEqual(set(artifact["proposals"][0]["triager"]["evidence"]),
                                 set(PHASE_EVIDENCE[phase]))

    def test_missing_empty_or_foreign_category_is_rejected(self):
        for phase in PROPOSAL_PHASES:
            categories = PHASE_EVIDENCE[phase]
            full = dict.fromkeys(categories, "grounds")
            broken = [{k: v for k, v in full.items() if k != name} for name in categories]
            broken += [{**full, name: "  "} for name in categories] + [{**full, "other": "x"}]
            if phase == "verification_design":
                broken.append({**full, "design": "filler"})
            for bad in broken:
                with self.subTest(phase=phase, bad=sorted(bad)):
                    with self.assertRaises(ValueError):
                        propose(*propose_args(phase, documents=bad))
                    with self.assertRaises(ValueError):
                        propose(*propose_args(phase, evidence=bad))


if __name__ == "__main__":
    unittest.main()
