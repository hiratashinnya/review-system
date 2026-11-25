"""Regression matrix for consecutive raw blocks and ended list containers."""
import unittest
from types import SimpleNamespace

from karte.ac_snapshot import from_issue_body, digest
from karte.ac_snapshot_html import advance
from karte.ac_check_update import plan
from karte.errors import KarteUsageError


class ConsecutiveHtmlTest(unittest.TestCase):
    def test_root_blocks_do_not_leak_list_context(self):
        for first in ("<pre>\nexample\n</pre>\n", "<?\nexample\n?>\n",
                      "<![CDATA[\nexample\n]]>\n", "<!DOCTYPE\nexample\n>\n",
                      "<div>\nexample\n</div>\n\n"):
            for fake in ("- [ ] example only", "## Notes"):
                for checked in (" ", "x"):
                    with self.subTest(first=first, fake=fake, checked=checked):
                        second = "  <div>" if first.startswith("<div>") else "<span>"
                        close = "  </div>" if first.startswith("<div>") else "</span>"
                        body = ("## Acceptance criteria\n- [ ] AC1\n\n" + first
                                + second + "\n" + fake + "\n" + close
                                + f"\n\n- [{checked}] AC2\n")
                        items = from_issue_body(body)
                        checks = [i for i in items if i.checked is not None]
                        self.assertEqual([i.text.splitlines()[0] for i in checks], ["AC1", "AC2"])
                        self.assertEqual(checks[-1].checked, checked == "x")
                        self.assertNotEqual(digest(items), digest(from_issue_body(body.replace("AC2", "changed"))))

                        judgments = [SimpleNamespace(number=i, result="satisfied")
                                     for i in range(1, len(items) + 1)]
                        expected = body.replace("- [ ] AC1", "- [x] AC1").replace("- [ ] AC2", "- [x] AC2")
                        self.assertEqual(plan(body, body, judgments)[0], expected)
                        with self.assertRaises(KarteUsageError):
                            plan(body, body.replace("AC2", "changed"), judgments)
                        if checked == "x":
                            judgments[-1].result = "unverified"
                            with self.assertRaisesRegex(KarteUsageError, "オーナー判断"):
                                plan(body, body, judgments)


class HtmlTransitionContractTest(unittest.TestCase):
    def test_non_html_returns_three_values(self):
        for line in ("## Acceptance criteria", "- [ ] AC1", "", "Description"):
            with self.subTest(line=line):
                self.assertEqual(advance(None, line, True, boundary=True), (None, False, None))
        self.assertEqual(advance(None, "<pre>", False), (None, False, None))

    def test_html_start_continue_end_and_dedent(self):
        for opening, closing in (("<pre>", "</pre>"), ("<?", "?>"),
                                 ("<![CDATA[", "]]>"), ("<!DOCTYPE", ">"),
                                 ("<div>", ""), ("<span>", "")):
            with self.subTest(opening=opening):
                block, raw, container = advance(None, opening, True, boundary=True)
                self.assertIsNotNone(block)
                self.assertTrue(raw)
                self.assertEqual(container, 0)
                self.assertEqual(advance(block, "example", True), (block, True, 0))
                self.assertEqual(advance(block, closing, True), (None, bool(closing), 0))
        block, raw, container = advance(None, "  <div>", True, list_indent=2)
        self.assertTrue(raw)
        self.assertEqual(container, 2)
        self.assertEqual(advance(block, "- [ ] AC2", True, list_indent=2), (None, False, None))
        self.assertEqual(advance(None, "<pre>x</pre>", True), (None, True, 0))
        self.assertEqual(advance(None, "<span>", True, boundary=False), (None, False, None))

    def test_normal_body_no_ac_and_non_checkbox(self):
        body = "## Acceptance criteria\n- [ ] AC1\n"
        items = from_issue_body(body)
        self.assertEqual([(i.text, i.checked) for i in items], [("AC1", False)])
        self.assertEqual(plan(body, body, [SimpleNamespace(number=1, result="satisfied")]),
                         (body.replace("[ ]", "[x]"), [1]))
        self.assertEqual(from_issue_body("# Issue\nDescription\n"), ())
        prose = "## Acceptance criteria\nDescription\n"
        self.assertEqual(plan(prose, prose, [SimpleNamespace(number=1, result="satisfied")]),
                         (prose, []))
