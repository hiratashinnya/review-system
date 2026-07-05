"""backref.locate — YAML フェンス・edges 範囲・本文範囲の特定。"""

import unittest

from backref import locate
from backref.errors import BackrefError

BLOCK = """\
## FND-1: x

<details><summary>⬡ FND-1 · v0.1.0</summary>

```yaml
id: FND-1
type: FND
labels: []
scheduled: ""
edges:
  - to: I-1
    ref_version: "0.1"
  - to: FR-1
    ref_version: "0.3"
```
</details>

本文の一行目。
**指摘時 ref_version**: 既存の記録。

---
"""

EMPTY_EDGES = """\
## P-1: y

<details><summary>⬡ P-1 · v0.3.0</summary>

```yaml
id: P-1
type: P
edges: []
```
</details>

本文。
"""


class TestLocateBlockForm(unittest.TestCase):
    def setUp(self):
        self.lines = BLOCK.splitlines()
        self.summary = next(i for i, l in enumerate(self.lines) if "<summary" in l)
        self.block = locate.find_yaml_block(self.lines, self.summary, "FND-1")

    def test_fence_bounds(self):
        self.assertTrue(self.lines[self.block.fence_open].strip().startswith("```"))
        self.assertEqual(self.lines[self.block.fence_close].strip(), "```")

    def test_find_key_line(self):
        idx = locate.find_key_line(self.lines, self.block, "type")
        self.assertEqual(self.lines[idx].strip(), "type: FND")
        self.assertIsNone(locate.find_key_line(self.lines, self.block, "resolved"))

    def test_edges_span_block(self):
        span = locate.find_edges_span(self.lines, self.block)
        self.assertFalse(span.inline)
        self.assertEqual(self.lines[span.start].strip(), "edges:")
        self.assertEqual(self.lines[span.end].strip(), 'ref_version: "0.3"')
        self.assertEqual(span.entry_indent, 2)

    def test_edge_targets(self):
        span = locate.find_edges_span(self.lines, self.block)
        self.assertEqual(locate.edge_targets(self.lines, span), {"I-1", "FR-1"})

    def test_body_region_includes_dd3(self):
        region = locate.find_body_region(self.lines, self.summary)
        body = "\n".join(self.lines[region.start : region.end + 1])
        self.assertIn("本文の一行目", body)
        self.assertIn("**指摘時 ref_version**", body)
        self.assertNotIn("---", body)


class TestLocateInlineEmptyEdges(unittest.TestCase):
    def setUp(self):
        self.lines = EMPTY_EDGES.splitlines()
        self.summary = next(i for i, l in enumerate(self.lines) if "<summary" in l)
        self.block = locate.find_yaml_block(self.lines, self.summary, "P-1")

    def test_inline(self):
        span = locate.find_edges_span(self.lines, self.block)
        self.assertTrue(span.inline)
        self.assertEqual(span.start, span.end)
        self.assertEqual(locate.edge_targets(self.lines, span), set())


class TestLocateFailClose(unittest.TestCase):
    def test_not_summary_line(self):
        lines = ["just text", "more"]
        with self.assertRaises(BackrefError):
            locate.find_yaml_block(lines, 0, "X")

    def test_no_details_close(self):
        lines = "<details><summary>⬡ X · v0.1.0</summary>\n```yaml\nid: X\n```".splitlines()
        with self.assertRaises(BackrefError):
            locate.find_body_region(lines, 0)


if __name__ == "__main__":
    unittest.main()
