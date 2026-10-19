"""ST-TC: 永続化から下流照合までの価値経路。"""
import tempfile
import unittest
from pathlib import Path
from issue_envelope.check import check
from issue_envelope.handoff import BINDINGS
from issue_envelope.store import write
from .fixtures import artifact


class EnvelopeAcceptanceTests(unittest.TestCase):
    def create(self, root):
        for kind, prefix, directory in (("VerificationDesign", "VD", "verification_design"),
                                         ("ChangePlan", "CP", "change_plan")):
            parent = artifact(kind, children=[f"{prefix}-371-tool"])
            child = artifact(kind, identifier=f"{prefix}-371-tool", parent=f"{prefix}-371")
            if kind == "ChangePlan":
                for node in (parent, child):
                    node["work_units"][0]["ac_refs"] = ["ST-TD-1"]
                    node["input_refs"] = ["VD-371"]
            write(root / directory / f"{prefix}-371.toml", parent)
            write(root / "tool" / directory / f"{prefix}-371.toml", child)
        return parent

    def test_persistent_plan_is_bound_and_missing_output_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.create(root)
            expected = {key: plan[key] for key in BINDINGS}
            expected["ac_refs"] = ["ST-TD-1"]
            self.assertEqual(check(root, {plan["id"]: expected}), [])
            expected["snapshot_oid"] = "c" * 40
            self.assertTrue(any("stale" in error for error in check(root, {plan["id"]: expected})))
            self.assertTrue(any("欠落" in error for error in check(root, {"CP-999": expected})))

    def test_unknown_ac_and_missing_reference_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create(root)
            path = root / "change_plan/CP-371.toml"
            text = path.read_text().replace('"ST-TD-1"', '"unknown-ac"')
            text = text.replace('input_refs = ["VD-371"]', 'input_refs = ["VD-999"]')
            path.write_text(text)
            errors = check(root)
            self.assertTrue(any("AC未対応" in error for error in errors))
            self.assertTrue(any("参照欠落" in error for error in errors))
