"""dsv2: #81 フィールドの meta.json 集約と drift の suppress:[RULE-004] 尊重。"""

import tempfile
import unittest
from pathlib import Path

from dsv2 import meta, query


def _write(root: Path, rel: str, yaml_text: str):
    y = root / rel
    y.parent.mkdir(parents=True, exist_ok=True)
    y.write_text(yaml_text, "utf-8")
    y.with_suffix(".md").write_text("body\n", "utf-8")
    return y


class TestFieldAggregation(unittest.TestCase):
    def test_aggregates_suppress_reason_carrier(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            y = _write(root, "nodes/04-verification/verify/x.yaml",
                       'title: t\nversion: "0.1.0"\n'
                       'suppress: [RULE-004]\nsuppress_reason: "凍結免除"\n'
                       'carrier: skill\nedges: []\n')
            node = meta.read_node(y, root)
        self.assertEqual(node["suppress"], ["RULE-004"])
        self.assertEqual(node["suppress_reason"], "凍結免除")
        self.assertEqual(node["carrier"], "skill")

    def test_aggregates_tr_result_log_ref(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            y = _write(root, "nodes/04-verification/tr/x.yaml",
                       'title: t\nversion: "0.1.0"\nresult: PASS\nlog_ref: "ci/log"\nedges: []\n')
            node = meta.read_node(y, root)
        self.assertEqual(node["result"], "PASS")
        self.assertEqual(node["log_ref"], "ci/log")

    def test_no_suppress_defaults_empty_and_omits_optionals(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            y = _write(root, "nodes/02-what/spec/x.yaml",
                       'title: t\nversion: "0.1.0"\nedges: []\n')
            node = meta.read_node(y, root)
        self.assertEqual(node["suppress"], [])
        for k in ("suppress_reason", "result", "log_ref", "carrier"):
            self.assertNotIn(k, node)


def _meta(nodes):
    return {"format": "doc-system-v2", "root": "r", "nodes": nodes}


class TestDriftSuppress(unittest.TestCase):
    """RULE-004 は always_error でないため suppress 可能。suppress:[RULE-004] の辺は drift 免除。"""

    target = {"id": "target", "type": "spec", "version": "0.2.0", "edges": [],
              "yaml_path": "nodes/02-what/spec/target.yaml"}

    def _src(self, suppress):
        # ref "0.1" ≠ target v0.2 → 本来ドリフト
        return {"id": "src", "type": "verify", "version": "0.1.0", "suppress": suppress,
                "yaml_path": "nodes/04-verification/verify/src.yaml",
                "edges": [{"to": "target", "ref_version": "0.1"}]}

    def test_drift_flagged_without_suppress(self):
        self.assertEqual(len(query.drift(_meta([self._src([]), self.target]))), 1)

    def test_drift_suppressed_with_rule004(self):
        self.assertEqual(query.drift(_meta([self._src(["RULE-004"]), self.target])), [])

    def test_deps_drift_true_without_suppress(self):
        rows = query.deps(_meta([self._src([]), self.target]), "src")
        self.assertIs(rows[0]["drift"], True)

    def test_deps_drift_none_when_suppressed(self):
        rows = query.deps(_meta([self._src(["RULE-004"]), self.target]), "src")
        self.assertIsNone(rows[0]["drift"])

    def test_dependents_drift_none_when_src_suppressed(self):
        rows = query.dependents(_meta([self._src(["RULE-004"]), self.target]), "target")
        self.assertIsNone(rows[0]["drift"])

    def test_orphans_ignores_suppress(self):
        # RULE-005（always_error）は suppress 無視: suppress を持つ孤立ノードも孤立として出る
        lonely = {"id": "lonely", "type": "spec", "version": "0.1.0",
                  "suppress": ["RULE-005"], "edges": []}
        self.assertEqual([n["id"] for n in query.orphans(_meta([lonely]))], ["lonely"])


if __name__ == "__main__":
    unittest.main()
