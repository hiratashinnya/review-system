"""docidx.query — 検索・依存先/依存元・ドリフト判定。"""

import unittest

from docidx import query
from docidx.model import Edge, Node, NodeIndex


def _node(nid, ntype, version="1.0", edges=(), labels=(), heading="", body=""):
    return Node(
        id=nid, type=ntype, version=version, heading=heading or nid,
        file="doc-system/x.md", line=1, labels=tuple(labels),
        edges=tuple(Edge(*e) for e in edges), body=body,
    )


class QueryBase(unittest.TestCase):
    def setUp(self):
        nodes = [
            _node("FR-1", "FR", "0.3", heading="レビュー実行"),
            _node("SPEC-1", "SPEC", "0.3", edges=[("FR-1", "0.3")], heading="正常系",
                  body="ドリフトを検出する"),
            _node("SPEC-2", "SPEC", "0.1", edges=[("FR-1", "0.1")], heading="境界",
                  labels=["post-mvp"]),
            _node("FND-9", "FND", "0.1", edges=[("MISSING-1", "0.1")]),
        ]
        self.index = NodeIndex.build(nodes)


class TestSearch(QueryBase):
    def test_by_type(self):
        ids = [n.id for n in query.search(self.index, node_type="SPEC")]
        self.assertEqual(sorted(ids), ["SPEC-1", "SPEC-2"])

    def test_by_type_case_insensitive(self):
        self.assertEqual(len(query.search(self.index, node_type="spec")), 2)

    def test_by_label(self):
        ids = [n.id for n in query.search(self.index, label="post-mvp")]
        self.assertEqual(ids, ["SPEC-2"])

    def test_by_id_glob(self):
        ids = [n.id for n in query.search(self.index, id_glob="SPEC-*")]
        self.assertEqual(sorted(ids), ["SPEC-1", "SPEC-2"])

    def test_by_text_in_body(self):
        ids = [n.id for n in query.search(self.index, text="ドリフト")]
        self.assertEqual(ids, ["SPEC-1"])

    def test_and_of_filters(self):
        hits = query.search(self.index, node_type="SPEC", label="post-mvp")
        self.assertEqual([n.id for n in hits], ["SPEC-2"])


class TestDeps(QueryBase):
    def test_outgoing_with_no_drift(self):
        rows = query.deps(self.index, "SPEC-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["to"], "FR-1")
        self.assertIs(rows[0]["drift"], False)
        self.assertIs(rows[0]["exists"], True)

    def test_drift_detected(self):
        # SPEC-2 は ref 0.1 だが FR-1 は 0.3 → ドリフト
        rows = query.deps(self.index, "SPEC-2")
        self.assertIs(rows[0]["drift"], True)

    def test_missing_target(self):
        rows = query.deps(self.index, "FND-9")
        self.assertIs(rows[0]["exists"], False)
        self.assertIsNone(rows[0]["drift"])

    def test_unknown_node(self):
        self.assertEqual(query.deps(self.index, "NOPE"), [])


class TestDependents(QueryBase):
    def test_reverse_index(self):
        rows = query.dependents(self.index, "FR-1")
        froms = sorted(r["from"] for r in rows)
        self.assertEqual(froms, ["SPEC-1", "SPEC-2"])

    def test_dependents_carry_drift(self):
        rows = {r["from"]: r for r in query.dependents(self.index, "FR-1")}
        self.assertIs(rows["SPEC-1"]["drift"], False)
        self.assertIs(rows["SPEC-2"]["drift"], True)

    def test_no_dependents(self):
        self.assertEqual(query.dependents(self.index, "SPEC-2"), [])


if __name__ == "__main__":
    unittest.main()
