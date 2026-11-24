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

    def test_script_and_style_blocks_are_raw_too(self):
        body = ("## Acceptance criteria\n- [ ] AC1\n<script>\n- [ ] fake\n</script>\n"
                "<style>\n## Fake\n</style>\n- [ ] AC2\n")
        items = from_issue_body(body)
        self.assertEqual([item.text.splitlines()[0] for item in items], ["AC1", "AC2"])


if __name__ == "__main__":
    unittest.main()
