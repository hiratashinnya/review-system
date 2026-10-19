"""IT-TC: 単一対象・中間scopeの全体復元と独立DAG検査。"""
import tempfile
import unittest
from pathlib import Path
from issue_envelope.graph import dag_errors, tree_errors
from issue_envelope.query import index, deps, dependents, orphans
from issue_envelope.store import load, write
from .fixtures import artifact


class EnvelopeGraphTests(unittest.TestCase):
    def tree(self, root):
        nodes = [artifact(identifier="VD-371", children=["VD-371-group"]),
                 artifact(identifier="VD-371-group", parent="VD-371",
                          children=["VD-371-tool"]),
                 artifact(identifier="VD-371-tool", parent="VD-371-group")]
        paths = [root / "verification_design/VD-371.toml",
                 root / "verification_design/VD-371-group.toml",
                 root / "tool/verification_design/VD-371.toml"]
        for path, data in zip(paths, nodes):
            write(path, data)
        return nodes

    def test_middle_group_and_leaf_are_same_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nodes = self.tree(root)
            records = load(root)
            self.assertEqual(len(records), 3)
            self.assertEqual(tree_errors(records), [])
            meta = index(root)
            self.assertTrue(all(edge["exists"] for edge in deps(meta, "VD-371-group")))
            self.assertTrue(dependents(meta, "VD-371-tool"))
            self.assertEqual(orphans(meta), [])
            self.assertEqual(set(nodes[0]), set(nodes[-1]))

    def test_single_target_still_has_root_and_leaf(self):
        root = artifact(children=["VD-371-tool"])
        leaf = artifact(identifier="VD-371-tool", parent="VD-371")
        self.assertEqual(tree_errors([(root, "root"), (leaf, "leaf")]), [])
        leaf["parent"] = "missing"
        self.assertTrue(tree_errors([(root, "root"), (leaf, "leaf")]))

    def test_containment_and_execution_cycles_are_separate(self):
        self.assertTrue(dag_errors({"WU-1": ["WU-2"], "WU-2": ["WU-1"]}, "work_units DAG"))
        self.assertTrue(dag_errors({"WU-1": ["absent"]}, "work_units DAG"))
        root = artifact(children=["VD-371-tool"])
        leaf = artifact(identifier="VD-371-tool", parent="VD-371")
        leaf["children"] = ["VD-371"]
        self.assertTrue(any("循環" in error for error in tree_errors([(root, ""), (leaf, "")])))

    def test_write_is_canonical_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "verification_design/VD-371.toml"
            write(path, artifact())
            self.assertEqual(load(directory)[0][0], artifact())
            with self.assertRaises(FileExistsError):
                write(path, artifact())
