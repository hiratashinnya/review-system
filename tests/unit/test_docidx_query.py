"""docidx.query — 検索・依存先/依存元・ドリフト判定。"""

import unittest

from docidx import query
from docidx.model import Edge, Node, NodeIndex


def _node(nid, ntype, version="1.0.0", edges=(), labels=(), heading="", body="",
          file="doc-system/x.md", line=1):
    return Node(
        id=nid, type=ntype, version=version, heading=heading or nid,
        file=file, line=line, labels=tuple(labels),
        edges=tuple(Edge(*e) for e in edges), body=body,
    )


class QueryBase(unittest.TestCase):
    def setUp(self):
        nodes = [
            _node("FR-1", "FR", "0.3.0", heading="レビュー実行"),
            _node("SPEC-1", "SPEC", "0.3.0", edges=[("FR-1", "0.3.0")], heading="正常系",
                  body="ドリフトを検出する"),
            _node("SPEC-2", "SPEC", "0.1.0", edges=[("FR-1", "0.1.0")], heading="境界",
                  labels=["post-mvp"]),
            _node("FND-9", "FND", "0.1.0", edges=[("MISSING-1", "0.1.0")]),
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
        # SPEC-2 は ref 0.1.0 だが FR-1 は 0.3.0 → x.y 不一致でドリフト
        rows = query.deps(self.index, "SPEC-2")
        self.assertIs(rows[0]["drift"], True)

    def test_z_bump_no_drift(self):
        # z バンプのみ（x.y 同一）は drift=False（RULE-004・DD-8 §4・FND-105）
        nodes = [
            _node("FR-1", "FR", "0.3.1"),  # z バンプ後
            _node("SPEC-1", "SPEC", "0.3.0", edges=[("FR-1", "0.3.0")]),  # ref は旧 z
        ]
        idx = NodeIndex.build(nodes)
        rows = query.deps(idx, "SPEC-1")
        self.assertIs(rows[0]["drift"], False)

    def test_minor_bump_drift(self):
        # y バンプは drift=True（伝播が必要）
        nodes = [
            _node("FR-1", "FR", "0.4.0"),
            _node("SPEC-1", "SPEC", "0.3.0", edges=[("FR-1", "0.3.0")]),
        ]
        idx = NodeIndex.build(nodes)
        rows = query.deps(idx, "SPEC-1")
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
        self.assertIs(rows["SPEC-1"]["drift"], False)  # x.y 一致
        self.assertIs(rows["SPEC-2"]["drift"], True)   # x.y 不一致（0.1 vs 0.3）

    def test_no_dependents(self):
        self.assertEqual(query.dependents(self.index, "SPEC-2"), [])


class TestDuplicateIds(unittest.TestCase):
    def test_first_wins_and_all_locations_recorded(self):
        nodes = [
            _node("SPEC-1", "SPEC", "0.3.0", heading="先（採用される）",
                  file="doc-system/a.md", line=10),
            _node("SPEC-1", "SPEC", "0.1.0", heading="後（捨てられる）",
                  file="doc-system/b.md", line=20),
            _node("FR-1", "FR", "0.3.0", file="doc-system/a.md", line=5),
        ]
        index = NodeIndex.build(nodes)
        # 先勝ち：by_id は最初の出現を保持
        self.assertEqual(index.by_id["SPEC-1"].heading, "先（採用される）")
        # 重複検知：捨てた側も含め全出現 file:line を出現順で記録
        self.assertEqual(
            index.duplicates,
            {"SPEC-1": ("doc-system/a.md:10", "doc-system/b.md:20")},
        )
        # 重複していない ID は duplicates に出ない
        self.assertNotIn("FR-1", index.duplicates)

    def test_no_duplicates_is_empty(self):
        index = NodeIndex.build([_node("FR-1", "FR")])
        self.assertEqual(index.duplicates, {})


if __name__ == "__main__":
    unittest.main()
