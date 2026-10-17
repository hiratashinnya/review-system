"""IT-TC: ref宣言・孤立検出と複数対象の同型復元。"""
import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path
from feedback_ledger.schema_types import DocSpec, Field, TableSpec
from feedback_ledger.tomlwrite import LINE, STRLIST
from harness_trace import build_index
from issue_envelope.cli import main
from issue_envelope.graph import tree_errors
from issue_envelope.query import deps, dependents, orphans
from issue_envelope.store import load, write
from .fixtures import artifact


class EnvelopeTraceTests(unittest.TestCase):
    def test_arbitrary_ref_field_uses_same_adapter(self):
        spec = DocSpec("custom", "v1", "", re.compile(".+"), (TableSpec("", (
            Field("id", LINE), Field("unexpected_field", STRLIST, False, ref="custom"))),))
        meta = build_index([(spec, {"id": "A", "unexpected_field": ["B"]}, "a"),
                            (spec, {"id": "B", "unexpected_field": []}, "b"),
                            (spec, {"id": "C", "unexpected_field": []}, "c")])
        self.assertTrue(deps(meta, "A")[0]["exists"])
        self.assertEqual(dependents(meta, "B")[0]["from"], "A")
        self.assertEqual([node["id"] for node in orphans(meta)], ["C"])

    def test_multiple_targets_restore_cp_and_vd_middle_nodes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for kind, prefix, folder in (("ChangePlan", "CP", "change_plan"),
                                          ("VerificationDesign", "VD", "verification_design")):
                nodes = [artifact(kind, children=[f"{prefix}-371-group"]),
                         artifact(kind, f"{prefix}-371-group", f"{prefix}-371",
                                  [f"{prefix}-371-a", f"{prefix}-371-b"]),
                         artifact(kind, f"{prefix}-371-a", f"{prefix}-371-group"),
                         artifact(kind, f"{prefix}-371-b", f"{prefix}-371-group")]
                for node in nodes:
                    node["scope"] = ["a", "b"] if node["children"] else [node["id"][-1]]
                    location = root if node["children"] else root / node["scope"][0]
                    filename = node["id"] if node["children"] else f"{prefix}-371"
                    write(location / folder / (filename + ".toml"), node)
            self.assertEqual(len(load(root)), 8)
            self.assertEqual(tree_errors(load(root)), [])

    def test_cli_exposes_orphans_and_requires_id_for_deps(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()) as output:
            write(Path(directory) / "test_design/TD-371.toml", artifact("TestDesign"))
            self.assertEqual(main(["orphans", "--repo", directory]), 0)
            self.assertIn("TD-371", output.getvalue())
            self.assertEqual(main(["deps", "--repo", directory]), 1)
