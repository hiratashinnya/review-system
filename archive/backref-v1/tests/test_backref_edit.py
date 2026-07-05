"""backref.edit — 純粋な行編集ヘルパと一括適用。"""

import unittest

from backref import edit
from backref.edit import Edit
from backref.errors import BackrefError


class TestBumpSummaryZ(unittest.TestCase):
    def test_bumps_patch(self):
        self.assertEqual(
            edit.bump_summary_z("<details><summary>⬡ FND-1 · v0.1.0</summary>"),
            "<details><summary>⬡ FND-1 · v0.1.1</summary>",
        )

    def test_bumps_two_digit(self):
        self.assertEqual(edit.bump_summary_z("⬡ X · v0.9.9"), "⬡ X · v0.9.10")

    def test_no_badge_raises(self):
        with self.assertRaises(BackrefError):
            edit.bump_summary_z("no badge here")


class TestXy(unittest.TestCase):
    def test_three_part(self):
        self.assertEqual(edit.xy("0.1.2"), "0.1")

    def test_two_part_passthrough(self):
        self.assertEqual(edit.xy("0.3"), "0.3")


class TestRenderEdgeEntry(unittest.TestCase):
    def test_default_indent(self):
        self.assertEqual(
            edit.render_edge_entry("FND-2", "0.1"),
            ["  - to: FND-2", '    ref_version: "0.1"'],
        )

    def test_custom_indent(self):
        self.assertEqual(
            edit.render_edge_entry("FND-2", "0.1", dash_indent=4),
            ["    - to: FND-2", '      ref_version: "0.1"'],
        )


class TestSetResolvedTrueLine(unittest.TestCase):
    def test_preserves_indent(self):
        self.assertEqual(edit.set_resolved_true_line("resolved: false"), "resolved: true")
        self.assertEqual(edit.set_resolved_true_line("  resolved: null"), "  resolved: true")


class TestApplyEdits(unittest.TestCase):
    def setUp(self):
        self.lines = ["a", "b", "c", "d", "e"]

    def test_replace_single(self):
        out = edit.apply_edits(self.lines, [Edit(1, 1, ["B"])])
        self.assertEqual(out, ["a", "B", "c", "d", "e"])

    def test_replace_range(self):
        out = edit.apply_edits(self.lines, [Edit(1, 3, ["X"])])
        self.assertEqual(out, ["a", "X", "e"])

    def test_insertion(self):
        # start == end+1 は挿入（範囲ゼロ置換）
        out = edit.apply_edits(self.lines, [Edit(2, 1, ["NEW"])])
        self.assertEqual(out, ["a", "b", "NEW", "c", "d", "e"])

    def test_append_at_end(self):
        out = edit.apply_edits(self.lines, [Edit(5, 4, ["Z"])])
        self.assertEqual(out, ["a", "b", "c", "d", "e", "Z"])

    def test_multiple_non_overlapping_apply_descending(self):
        out = edit.apply_edits(self.lines, [Edit(0, 0, ["A"]), Edit(4, 4, ["E", "F"])])
        self.assertEqual(out, ["A", "b", "c", "d", "E", "F"])

    def test_overlap_raises(self):
        with self.assertRaises(BackrefError):
            edit.apply_edits(self.lines, [Edit(1, 3, ["X"]), Edit(2, 2, ["Y"])])


if __name__ == "__main__":
    unittest.main()
