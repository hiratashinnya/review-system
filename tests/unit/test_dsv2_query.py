"""dsv2.query — deps / dependents / orphans / drift の契約。"""

import unittest

from dsv2 import meta, query

from tests.unit.dsv2_fixtures import make_tree


class TestQuery(unittest.TestCase):
    def setUp(self):
        self.meta = meta.build_meta(make_tree(self))

    def test_deps(self):
        rows = query.deps(self.meta, "child-spec")
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["to"], "parent-spec")
        self.assertTrue(r["exists"])
        self.assertFalse(r["drift"])  # ref 0.1 == parent 0.1.0 -> x.y 一致

    def test_deps_unknown_node_returns_none(self):
        self.assertIsNone(query.deps(self.meta, "nope"))

    def test_dependents(self):
        rows = query.dependents(self.meta, "parent-spec")
        self.assertEqual([r["from"] for r in rows], ["child-spec"])

    def test_orphans(self):
        orph = {n["id"] for n in query.orphans(self.meta)}
        self.assertEqual(orph, {"lonely"})  # parent は被参照・他は出辺あり

    def test_drift_none_when_consistent(self):
        self.assertEqual(query.drift(self.meta), [])

    def test_drift_detected(self):
        # child-spec の ref を 0.9 に書き換えて親 0.1 とドリフトさせる
        for n in self.meta["nodes"]:
            if n["id"] == "child-spec":
                n["edges"][0]["ref_version"] = "0.9"
        rows = query.drift(self.meta)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["from"], "child-spec")
        self.assertEqual(rows[0]["to"], "parent-spec")


def _drift_meta(nodes):
    return {"format": "doc-system-v2", "root": "r", "nodes": nodes}


class TestDriftUnconditional(unittest.TestCase):
    """issue #118: suppress 機構は廃止済み。drift（RULE-004）は node の type/属性に関わらず無条件発火する。

    かつて ``suppress: [RULE-004]`` を持つ VERIFY 等の凍結記録は drift 判定を免除されていたが、
    オーナー方針（依存先ノード更新時の影響確認は必須）によりその凍結免除機構自体を撤去した。
    """

    target = {"id": "target", "type": "spec", "version": "0.2.0", "edges": [],
              "yaml_path": "nodes/02-what/spec/target.yaml"}

    def _verify_src(self):
        # ref "0.1" ≠ target v0.2 → ドリフト。旧 suppress:[RULE-004] があれば免除されていたケース。
        return {"id": "src", "type": "verify", "version": "0.1.0",
                "yaml_path": "nodes/04-verification/verify/src.yaml",
                "edges": [{"to": "target", "ref_version": "0.1"}]}

    def test_drift_flagged_for_verify_type_source(self):
        self.assertEqual(len(query.drift(_drift_meta([self._verify_src(), self.target]))), 1)

    def test_deps_drift_true_for_verify_type_source(self):
        rows = query.deps(_drift_meta([self._verify_src(), self.target]), "src")
        self.assertIs(rows[0]["drift"], True)

    def test_dependents_drift_true_for_verify_type_source(self):
        rows = query.dependents(_drift_meta([self._verify_src(), self.target]), "target")
        self.assertIs(rows[0]["drift"], True)

    def test_orphans_unaffected_by_removed_suppress_mechanism(self):
        # RULE-005（孤立）は元々 suppress と無関係。廃止後も変わらず判定される。
        lonely = {"id": "lonely", "type": "spec", "version": "0.1.0", "edges": []}
        self.assertEqual([n["id"] for n in query.orphans(_drift_meta([lonely]))], ["lonely"])


def _prompt_node(node_id: str, carrier: str | None = "skill") -> dict:
    node = {"id": node_id, "type": "prompt", "version": "0.1.0", "edges": []}
    if carrier is not None:
        node["carrier"] = carrier
    return node


class TestPromptCoverageGaps(unittest.TestCase):
    """RULE-032: 宣言 skill 集合のうち対応 PROMPT ノードが無いものを列挙。"""

    def _meta(self, nodes):
        return {"format": "doc-system-v2", "root": "r", "nodes": nodes}

    def test_all_covered_returns_empty(self):
        m = self._meta([_prompt_node("align-認識合わせ"), _prompt_node("mvp-scope-価値ベース")])
        self.assertEqual(query.prompt_coverage_gaps(m, targets=["align", "mvp-scope"]), [])

    def test_missing_skill_is_reported(self):
        m = self._meta([_prompt_node("align-認識合わせ")])
        self.assertEqual(query.prompt_coverage_gaps(m, targets=["align", "docidx"]), ["docidx"])

    def test_preserves_declared_order(self):
        m = self._meta([])
        self.assertEqual(
            query.prompt_coverage_gaps(m, targets=["docidx", "align", "mvp-scope"]),
            ["docidx", "align", "mvp-scope"],
        )

    def test_non_skill_carrier_prompt_not_counted_as_coverage(self):
        # 著作エージェント PROMPT（carrier なし）は対象 skill の代替にならない
        m = self._meta([_prompt_node("align-author-著作支援", carrier=None)])
        self.assertEqual(query.prompt_coverage_gaps(m, targets=["align"]), ["align"])

    def test_prefix_boundary_no_false_match(self):
        # "spec-pipeline" ノードは "spec-principles" の充足にならない（ハイフン境界一致）
        m = self._meta([_prompt_node("spec-pipeline-オーケストレータ")])
        self.assertEqual(
            query.prompt_coverage_gaps(m, targets=["spec-principles", "spec-pipeline"]),
            ["spec-principles"],
        )

    def test_default_targets_used_when_omitted(self):
        gaps = query.prompt_coverage_gaps(self._meta([]))
        self.assertEqual(gaps, list(query.PROMPT_COVERAGE_TARGETS))


if __name__ == "__main__":
    unittest.main()
