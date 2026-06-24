"""docidx.nodeyaml — ノード YAML サブセットリーダの契約。"""

import unittest

from docidx import nodeyaml


class TestScalars(unittest.TestCase):
    def test_quoted_and_bare_strings(self):
        d = nodeyaml.parse('id: FR-1\ntype: FR\nscheduled: ""\n')
        self.assertEqual(d["id"], "FR-1")
        self.assertEqual(d["type"], "FR")
        self.assertEqual(d["scheduled"], "")

    def test_bool_int_null(self):
        d = nodeyaml.parse("resolved: true\ndisabled: false\nn: 3\nempty: null\n")
        self.assertIs(d["resolved"], True)
        self.assertIs(d["disabled"], False)
        self.assertEqual(d["n"], 3)
        self.assertIsNone(d["empty"])

    def test_quoted_version_stays_string(self):
        d = nodeyaml.parse('ref: "0.3"\n')
        self.assertEqual(d["ref"], "0.3")

    def test_inline_comment_stripped(self):
        d = nodeyaml.parse("suppress: [RULE-018]   # 理由\nid: X-1\n")
        self.assertEqual(d["suppress"], ["RULE-018"])
        self.assertEqual(d["id"], "X-1")


class TestLists(unittest.TestCase):
    def test_empty_inline_list(self):
        self.assertEqual(nodeyaml.parse("labels: []\n")["labels"], [])

    def test_nonempty_inline_list(self):
        d = nodeyaml.parse("labels: [post-mvp, experimental]\n")
        self.assertEqual(d["labels"], ["post-mvp", "experimental"])


class TestEdges(unittest.TestCase):
    def test_edges_block_list(self):
        text = (
            "id: SPEC-1\n"
            "type: SPEC\n"
            "edges:\n"
            "  - to: FR-1\n"
            '    ref_version: "0.3"\n'
            "  - to: FND-40\n"
            '    ref_version: "0.1"\n'
            '    note: "補足"\n'
        )
        d = nodeyaml.parse(text)
        self.assertEqual(len(d["edges"]), 2)
        self.assertEqual(d["edges"][0], {"to": "FR-1", "ref_version": "0.3"})
        self.assertEqual(d["edges"][1]["note"], "補足")

    def test_empty_edges(self):
        self.assertEqual(nodeyaml.parse("edges: []\n")["edges"], [])

    def test_comment_and_blank_lines_ignored(self):
        text = "id: X-1\n# コメント\n\ntype: X\n"
        d = nodeyaml.parse(text)
        self.assertEqual(d, {"id": "X-1", "type": "X"})


class TestErrors(unittest.TestCase):
    def test_missing_colon_raises(self):
        with self.assertRaises(nodeyaml.NodeYamlError):
            nodeyaml.parse("id FR-1\n")

    def test_edge_attr_before_dash_raises(self):
        with self.assertRaises(nodeyaml.NodeYamlError):
            nodeyaml.parse("edges:\n    ref_version: 0.1\n")


if __name__ == "__main__":
    unittest.main()
