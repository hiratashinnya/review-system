"""Regression matrix for consecutive raw blocks and ended list containers."""
import unittest

from karte.ac_snapshot import from_issue_body, digest


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
