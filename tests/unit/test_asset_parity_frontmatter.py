"""asset_parity.frontmatter — 最小スカラーフロントマターリーダーの契約。"""

import unittest

from asset_parity.frontmatter import read_frontmatter


class TestReadFrontmatter(unittest.TestCase):
    def test_plain_scalars(self):
        text = "---\nname: align\ndescription: Some description.\n---\n\nbody\n"
        fm = read_frontmatter(text)
        self.assertEqual(fm["name"], "align")
        self.assertEqual(fm["description"], "Some description.")

    def test_hyphenated_key(self):
        text = "---\nname: x\ndisable-model-invocation: true\n---\n"
        fm = read_frontmatter(text)
        self.assertEqual(fm["disable-model-invocation"], "true")

    def test_user_invocable_false(self):
        text = "---\nname: spec-principles\nuser-invocable: false\n---\n"
        fm = read_frontmatter(text)
        self.assertEqual(fm["user-invocable"], "false")

    def test_quoted_value_unquoted(self):
        text = "---\nname: 'quoted-name'\ndescription: \"a colon: inside\"\n---\n"
        fm = read_frontmatter(text)
        self.assertEqual(fm["name"], "quoted-name")
        self.assertEqual(fm["description"], "a colon: inside")

    def test_description_with_extra_colons(self):
        # 説明文中の追加コロンは値としてそのまま残る（key は最初のコロンまで）。
        text = "---\ndescription: NOT for X (use Y). See also: Z.\n---\n"
        fm = read_frontmatter(text)
        self.assertEqual(fm["description"], "NOT for X (use Y). See also: Z.")

    def test_no_leading_marker_returns_none(self):
        self.assertIsNone(read_frontmatter("# just a heading\n\nno frontmatter here\n"))

    def test_unterminated_block_returns_none(self):
        self.assertIsNone(read_frontmatter("---\nname: x\n\nno closing marker\n"))

    def test_leading_blank_lines_tolerated(self):
        text = "\n\n---\nname: x\n---\n"
        fm = read_frontmatter(text)
        self.assertEqual(fm["name"], "x")

    def test_comments_and_blank_lines_ignored(self):
        text = "---\n# a comment\nname: x\n\ndescription: y\n---\n"
        fm = read_frontmatter(text)
        self.assertEqual(fm, {"name": "x", "description": "y"})

    def test_list_items_skipped_not_crash(self):
        # tools: の下にリストがあっても（コロン無し行）落ちない。
        text = "---\nname: x\ntools:\n  - Read\n  - Grep\n---\n"
        fm = read_frontmatter(text)
        self.assertEqual(fm["name"], "x")
        self.assertNotIn("- Read", fm)


if __name__ == "__main__":
    unittest.main()
