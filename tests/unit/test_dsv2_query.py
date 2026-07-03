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


if __name__ == "__main__":
    unittest.main()
