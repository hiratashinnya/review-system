"""Raw HTML blocks in an AC section are text, never AC headings or checkboxes.

Regression for Codex P1 (r4681383555): a <pre> example after a real AC must not
add checkboxes or end the AC section.
"""
import unittest

from karte.ac_snapshot import from_issue_body


class RawHtmlBlockInAcSectionTest(unittest.TestCase):
    def test_pre_example_checkbox_and_heading_are_not_acs(self):
        body = ("## Acceptance criteria\n- [ ] AC1\n<pre>\n- [ ] example only\n"
                "## Notes\n</pre>\n- [ ] AC2\n")
        items = from_issue_body(body)
        self.assertEqual([item.text.splitlines()[0] for item in items], ["AC1", "AC2"])
        self.assertEqual([item.checked for item in items], [False, False])
        self.assertIn("example only", items[0].text)

    def test_changing_pre_example_is_not_a_checkbox_change(self):
        before = from_issue_body("## Acceptance criteria\n- [ ] AC1\n<pre>\n- [ ] ex\n</pre>\n")
        after = from_issue_body("## Acceptance criteria\n- [ ] AC1\n<pre>\n- [ ] other\n</pre>\n")
        self.assertEqual([item.text.splitlines()[0] for item in before], ["AC1"])
        self.assertNotEqual(before[0].text, after[0].text)

    def test_single_line_pre_does_not_swallow_following_ac(self):
        items = from_issue_body("## Acceptance criteria\n- [ ] AC1\n<pre>x</pre>\n- [ ] AC2\n")
        self.assertEqual([item.text.splitlines()[0] for item in items], ["AC1", "AC2"])

    def test_comment_opener_inside_pre_does_not_hide_following_ac(self):
        # Regression (Codex P1 r4681455581): an unterminated <!-- literal inside a raw
        # block must not start a comment that swallows the real AC2.
        body = "## Acceptance criteria\n- [ ] AC1\n<pre>\n<!-- literal\n</pre>\n- [ ] AC2\n"
        items = from_issue_body(body)
        self.assertEqual([item.text.splitlines()[0] for item in items], ["AC1", "AC2"])
        self.assertIn("<!-- literal", items[0].text)

    def test_script_and_style_blocks_are_raw_too(self):
        body = ("## Acceptance criteria\n- [ ] AC1\n<script>\n- [ ] fake\n</script>\n"
                "<style>\n## Fake\n</style>\n- [ ] AC2\n")
        items = from_issue_body(body)
        self.assertEqual([item.text.splitlines()[0] for item in items], ["AC1", "AC2"])

    def test_div_and_other_block_tags_hide_examples_until_blank(self):
        for tag in ("div", "table", "details", "section", "custom-tag"):
            for example in ("- [ ] example only", "## Notes"):
                with self.subTest(tag=tag, example=example):
                    body = ("## Acceptance criteria\n- [ ] AC1\n\n"
                            f"<{tag}>\n{example}\n</{tag}>\n\n- [ ] AC2\n")
                    items = from_issue_body(body)
                    self.assertEqual([item.text.splitlines()[0] for item in items],
                                     ["AC1", "AC2"])
                    self.assertEqual([item.checked for item in items], [False, False])
                    self.assertNotEqual(items, from_issue_body(body.replace("AC2", "changed")))

    def test_other_raw_block_terminators(self):
        for start, end in (("<?", "?>"), ("<![CDATA[", "]]>"), ("<!DOCTYPE", ">")):
            with self.subTest(start=start):
                body = ("## Acceptance criteria\n- [ ] AC1\n"
                        f"{start}\n## Notes\n- [ ] fake\n{end}\n- [ ] AC2\n")
                items = from_issue_body(body)
                self.assertEqual([item.text.splitlines()[0] for item in items],
                                 ["AC1", "AC2"])

    def test_type7_after_block_boundaries(self):
        for prefix in ("", "- [ ] AC1\n\n### Example\n",
                       "- [ ] AC1\n\n```\ncode\n```\n"):
            for fake in ("- [ ] example only", "## Notes"):
                with self.subTest(prefix=prefix, fake=fake):
                    body = ("## Acceptance criteria\n" + prefix +
                            f"<span>\n{fake}\n</span>\n\n- [ ] AC2\n")
                    items = from_issue_body(body)
                    checked = [item.text.splitlines()[0] for item in items
                               if item.checked is not None]
                    self.assertEqual(checked, (["AC1"] if prefix else []) + ["AC2"])

    def test_type7_does_not_interrupt_paragraph(self):
        body = ("## Acceptance criteria\n- [ ] AC1\n  prose\n"
                "  <span>\n- [ ] AC2\n")
        items = from_issue_body(body)
        self.assertEqual([item.checked for item in items], [False, False])

    def test_html_container_ends_at_sibling(self):
        for tag in ("div", "pre"):
            body = ("## Acceptance criteria\n- [ ] AC1\n"
                    f"  <{tag}>\n  example\n  </{tag}>\n- [x] AC2\n")
            items = from_issue_body(body)
            self.assertEqual([item.text.splitlines()[0] for item in items], ["AC1", "AC2"])
            self.assertEqual([item.checked for item in items], [False, True])


if __name__ == "__main__":
    unittest.main()
