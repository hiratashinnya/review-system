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


class TestOptionalFieldAggregation(unittest.TestCase):
    """#81 で正式化した任意フィールドの集約（suppress/suppress_reason は #118 で廃止済み）。"""

    def _write(self, root, rel, yaml_text):
        from pathlib import Path
        y = root / rel
        y.parent.mkdir(parents=True, exist_ok=True)
        y.write_text(yaml_text, "utf-8")
        y.with_suffix(".md").write_text("body\n", "utf-8")
        return y

    def test_aggregates_carrier_result_log_ref(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            y = self._write(root, "nodes/04-verification/tr/x.yaml",
                             'title: t\nversion: "0.1.0"\nresult: PASS\n'
                             'log_ref: "ci/log"\ncarrier: skill\nedges: []\n')
            node = meta.read_node(y, root)
        self.assertEqual(node["result"], "PASS")
        self.assertEqual(node["log_ref"], "ci/log")
        self.assertEqual(node["carrier"], "skill")

    def test_suppress_field_absent_entirely(self):
        """suppress/suppress_reason は issue #118 で機構ごと廃止。存在しても集約しない。"""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            y = self._write(root, "nodes/02-what/spec/x.yaml",
                             'title: t\nversion: "0.1.0"\nedges: []\n')
            node = meta.read_node(y, root)
        for k in ("suppress", "suppress_reason", "result", "log_ref", "carrier"):
            self.assertNotIn(k, node)


class TestBodyPolicyAggregation(unittest.TestCase):
    """body_policy に従い bodyless/shared-body を meta へ集約する。"""

    def _write_yaml(self, root, rel, text):
        y = root / rel
        y.parent.mkdir(parents=True, exist_ok=True)
        y.write_text(text, "utf-8")
        return y

    def test_bodyless_node_has_no_required_body_path(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            y = self._write_yaml(root, "nodes/04-verification/tc/bodyless.yaml",
                                 'title: t\nversion: "0.1.0"\nedges: []\n')
            node = meta.read_node(y, root)
        self.assertEqual(node["body_policy"], "none")
        self.assertIsNone(node["body_path"])

    def test_shared_body_ref_is_resolved(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shared = root / "nodes/04-verification/td/shared.md"
            shared.parent.mkdir(parents=True, exist_ok=True)
            shared.write_text("# shared\n", "utf-8")
            y = self._write_yaml(root, "nodes/04-verification/td/td-a.yaml",
                                 'title: t\nversion: "0.1.0"\n'
                                 'body_ref.file: "nodes/04-verification/td/shared.md"\n'
                                 'body_ref.anchor: "case-a"\nedges: []\n')
            node = meta.read_node(y, root)
        self.assertEqual(node["body_policy"], "shared")
        self.assertEqual(node["body_path"], "nodes/04-verification/td/shared.md")
        self.assertEqual(node["body_anchor"], "case-a")


class TestPlacementValidation(unittest.TestCase):
    """read_node は不正配置を silently 誤メタ化せず MetaError で fail-close する。"""

    def _make(self, tmp, relpath):
        import tempfile
        from pathlib import Path
        root = Path(tempfile.mkdtemp(dir=tmp))
        y = root / relpath
        y.parent.mkdir(parents=True, exist_ok=True)
        y.write_text("title: t\nversion: 0.1.0\nedges: []\n", "utf-8")
        y.with_suffix(".md").write_text("body\n", "utf-8")
        return root, y

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()

    def test_valid_placements_ok(self):
        for rel in ("nodes/02-what/spec/x.yaml",
                    "nodes/04-verification/fnd/open/x.yaml",
                    "nodes/04-verification/pend/deferred/x.yaml"):
            root, y = self._make(self._tmp, rel)
            meta.read_node(y, root)  # 例外なし

    def test_unknown_stage(self):
        root, y = self._make(self._tmp, "nodes/99-bogus/spec/x.yaml")
        self.assertRaises(meta.MetaError, meta.read_node, y, root)

    def test_type_not_in_stage(self):
        root, y = self._make(self._tmp, "nodes/02-what/fnd/x.yaml")  # fnd は 04 のみ
        self.assertRaises(meta.MetaError, meta.read_node, y, root)

    def test_status_dir_on_statusless_type(self):
        root, y = self._make(self._tmp, "nodes/05-design/mod/extra/x.yaml")
        self.assertRaises(meta.MetaError, meta.read_node, y, root)

    def test_missing_required_status_dir(self):
        root, y = self._make(self._tmp, "nodes/04-verification/fnd/x.yaml")  # status 必須
        self.assertRaises(meta.MetaError, meta.read_node, y, root)

    def test_unknown_status_value(self):
        root, y = self._make(self._tmp, "nodes/04-verification/fnd/bogus/x.yaml")
        self.assertRaises(meta.MetaError, meta.read_node, y, root)


if __name__ == "__main__":
    unittest.main()
