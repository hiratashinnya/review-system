"""Issue #783 F-783-07: approved materials follow the per-phase reviewer, prior receipts and reviewed artifact."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from finding_triager.approved_materials import approved_materials
from triage_policy.phases import PHASE_ROUTES, PROPOSAL_PHASES

FILES = {"verification_design": "vd.toml", "solution_planning": "cp.toml", "test_design": "td.toml"}
BOUND = {"issue": 783, "run_id": "run", "target_key": "key", "snapshot_oid": "a" * 40}
MODULE = "finding_triager.approved_materials."


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PhaseMaterialsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for key, name in FILES.items():
            kind = PHASE_ROUTES[key]["artifact_type"]
            (self.root / name).write_text('artifact_type = "' + kind + '"\n')

    def build(self, phase, kind=None, declared=None, drop=()):
        route = PHASE_ROUTES[phase]
        reviewed = self.root / FILES[route["reviewed"]]
        (self.root / "binding.json").write_text(json.dumps({
            "artifact": reviewed.name, "artifact_digest": digest(reviewed),
            "expected": {**BOUND, "artifact_type": kind or route["artifact_type"]}}))
        receipts = [{"phase": key, "artifact": FILES[key], "artifact_digest": digest(self.root / FILES[key])}
                    for key in route["prior"] if key not in drop]
        approval = {**BOUND, "context_id": "owner-approved", "reviews": receipts}
        if declared:
            approval["triage_phase"] = declared
        return {"binding_file": "binding.json", "approval_file": "approval.json"}, approval

    def run_with(self, approval, marker, phase=None):
        with patch(MODULE + "validate_phase_dispatch", return_value=approval) as validate, \
             patch(MODULE + "read_committed_artifact", side_effect=lambda p, r: p.read_bytes()), \
             patch(MODULE + "normalize", side_effect=lambda doc: {**doc, **BOUND}):
            result = approved_materials(self.root, marker, phase)
        self.validate = validate
        return result

    def test_each_phase_exports_prior_and_reviewed_with_its_reviewer(self):
        for phase in PROPOSAL_PHASES:
            route = PHASE_ROUTES[phase]
            marker, approval = self.build(phase)
            with self.subTest(phase=phase):
                result = self.run_with(approval, marker, phase)
                self.validate.assert_called_once_with(marker, route["reviewer"], self.root.resolve())
                self.assertEqual(set(result["materials"]), {*route["prior"], route["reviewed"]})
                reviewed = result["materials"][route["reviewed"]]
                self.assertEqual(reviewed["sha256"], result["input_digest"])
                self.assertIn(route["artifact_type"], reviewed["content"])

    def test_first_review_needs_no_prior_receipt(self):
        marker, approval = self.build("verification_design")
        self.assertEqual(approval["reviews"], [])
        self.assertEqual(list(self.run_with(approval, marker, "verification_design")["materials"]),
                         ["verification_design"])

    def test_implementation_review_default_follows_declared_phase(self):
        for declared in ("review", "remediation_review", None):
            marker, approval = self.build("review", declared=declared)
            with self.subTest(declared=declared):
                result = self.run_with(approval, marker)
                self.assertEqual(result["triage_phase"], declared)
                self.assertEqual(set(result["materials"]), {"verification_design", "solution_planning"})

    def test_missing_prior_receipt_is_rejected(self):
        for phase in PROPOSAL_PHASES:
            for key in PHASE_ROUTES[phase]["prior"]:
                marker, approval = self.build(phase, drop=(key,))
                with self.subTest(phase=phase, missing=key), self.assertRaisesRegex(ValueError, "missing prior"):
                    self.run_with(approval, marker, phase)

    def test_changed_reviewed_or_prior_artifact_is_rejected(self):
        for phase in PROPOSAL_PHASES:
            route = PHASE_ROUTES[phase]
            for key in {route["reviewed"], *route["prior"]}:
                marker, approval = self.build(phase)
                path = self.root / FILES[key]
                original = path.read_text()
                path.write_text(original + "# changed\n")
                with self.subTest(phase=phase, changed=key), self.assertRaisesRegex(ValueError, "digest"):
                    self.run_with(approval, marker, phase)
                path.write_text(original)

    def test_phase_artifact_type_and_declaration_mismatch_are_rejected(self):
        marker, approval = self.build("review")
        for phase in ("verification_design", "test_design"):
            with self.subTest(phase=phase), self.assertRaisesRegex(ValueError, "artifact type"):
                self.run_with(approval, marker, phase)
        marker, approval = self.build("review", kind="TestDesign")
        with self.assertRaisesRegex(ValueError, "artifact type"):
            self.run_with(approval, marker, "review")
        for phase, declared in (("review", "remediation_review"), ("remediation_review", "review")):
            marker, approval = self.build(phase, declared=declared)
            with self.subTest(phase=phase, declared=declared), self.assertRaises(ValueError):
                self.run_with(approval, marker, phase)
        marker, approval = self.build("review", declared="verification_design")
        with self.assertRaises(ValueError):
            self.run_with(approval, marker)

    def test_unknown_phase_is_rejected_before_any_approval_is_read(self):
        marker, approval = self.build("review")
        for phase in ("planning", "", 3, ["review"]):
            with self.subTest(phase=phase), patch(MODULE + "validate_phase_dispatch") as validate:
                with self.assertRaises(ValueError):
                    approved_materials(self.root, marker, phase)
                validate.assert_not_called()

    def test_implementation_review_requires_reviewed_digest_to_match_receipt(self):
        marker, approval = self.build("review")
        binding = json.loads((self.root / "binding.json").read_text())
        binding["artifact_digest"] = "f" * 64
        (self.root / "binding.json").write_text(json.dumps(binding))
        with self.assertRaisesRegex(ValueError, "differs"):
            self.run_with(approval, marker, "review")


if __name__ == "__main__":
    unittest.main()
