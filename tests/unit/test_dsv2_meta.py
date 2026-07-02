"""dsv2.meta — nodes/** 走査と meta.json 生成の契約。"""

import json
import unittest

from dsv2 import meta

from tests.unit.dsv2_fixtures import make_tree


class TestBuildMeta(unittest.TestCase):
    def setUp(self):
        self.root = make_tree(self)

    def test_scans_all_nodes(self):
        m = meta.build_meta(self.root)
        ids = {n["id"] for n in m["nodes"]}
        self.assertEqual(
            ids,
            {"parent-spec", "child-spec", "target-p", "fnd-open", "lonely"},
        )

    def test_path_derived_facets(self):
        m = meta.build_meta(self.root)
        by_id = meta.index_by_id(m)
        fnd = by_id["fnd-open"]
        self.assertEqual(fnd["stage"], "04-verification")
        self.assertEqual(fnd["type"], "fnd")
        self.assertEqual(fnd["status"], "open")
        spec = by_id["child-spec"]
        self.assertEqual(spec["type"], "spec")
        self.assertIsNone(spec["status"])  # spec は lifecycle なし

    def test_sidecar_fields(self):
        m = meta.build_meta(self.root)
        by_id = meta.index_by_id(m)
        child = by_id["child-spec"]
        self.assertEqual(child["title"], "子 SPEC のタイトル")
        self.assertEqual(child["version"], "0.1.1")
        self.assertEqual(child["condition"], "failure")
        self.assertEqual(child["edges"], [{"to": "parent-spec", "ref_version": "0.1"}])
        self.assertEqual(child["body_path"], "nodes/02-what/spec/child-spec.md")

    def test_write_and_load_roundtrip(self):
        out = self.root / "meta.json"
        meta.write_meta(self.root, out)
        self.assertTrue(out.exists())
        loaded = json.loads(out.read_text("utf-8"))
        self.assertEqual(len(loaded["nodes"]), 5)
        # load_meta prefers the written file
        again = meta.load_meta(self.root, out)
        self.assertEqual(again, loaded)

    def test_load_meta_builds_when_absent(self):
        m = meta.load_meta(self.root, self.root / "nope.json")
        self.assertEqual(len(m["nodes"]), 5)


if __name__ == "__main__":
    unittest.main()
