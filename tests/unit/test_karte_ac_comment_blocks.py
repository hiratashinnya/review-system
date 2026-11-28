"""Root HTML comments must end blocks without leaking old list state."""
import unittest
from itertools import product
from types import SimpleNamespace

from karte.ac_snapshot import from_issue_body, digest
from karte.ac_check_update import plan
from karte.errors import KarteUsageError
from tests.unit.test_karte_ac_state_boundaries import boundary_cases

FIRST = "## Acceptance criteria\n- [ ] AC1\n"


def comment_cases():
    for tag, fake, comment, before, after, checked in product(
        ("span", "div"), ("- [ ] example only", "## Notes"),
        ("<!-- example -->\n", "<!--\nexample\n-->\n"),
        ("", "\n"), ("", "\n"), (" ", "x"),
    ):
        opening, closing = ("<span>", "</span>") if tag == "span" else ("  <div>", "  </div>")
        body = FIRST + before + comment + after + f"{opening}\n{fake}\n{closing}\n\n- [{checked}] AC2\n"
        yield body, ["AC1", "AC2"], "AC2"
    for tail in (
        "  <!-- example -->\n  <div>\n  example\n  </div>\n- [x] AC2\n",
        "  <!--\n  example\n  -->\n  <span>\n  example\n  </span>\n- [x] AC2\n",
        "  <!--\n  example\n- [x] AC2\n",
        "  <!--\n  example\n<span>\n- [ ] example only\n</span>\n\n- [x] AC2\n",
        "<!-- first --> <!-- second -->\n- [x] AC2\n",
    ):
        yield FIRST + tail, ["AC1", "AC2"], "AC2"
    yield FIRST.rstrip("\n") + " <!-- inline -->\n  <span>\n- [x] AC2\n", ["AC1", "AC2"], "AC2"
    yield FIRST.rstrip("\n") + " <!-- inline\n  example\n  -->\n  <span>\n- [x] AC2\n", ["AC1", "AC2"], "AC2"
    yield FIRST + "<!-- note -->visible text\n- [x] AC2\n", ["AC1", "AC2"], "visible text"
    yield from boundary_cases()


class CommentBlockBoundaryTest(unittest.TestCase):
    def test_comment_blocks_preserve_ac_coverage_and_write_positions(self):
        for body, names, drift in comment_cases():
            with self.subTest(body=body):
                items = from_issue_body(body)
                checks = [i for i in items if i.checked is not None]
                self.assertEqual([i.text.split()[0] for i in checks], names)
                self.assertEqual([i.checked for i in checks], [False, "- [x] AC2" in body])
                judgments = [SimpleNamespace(number=i, result="satisfied") for i in range(1, len(items) + 1)]
                expected = body.replace("[ ] AC1", "[x] AC1").replace("[ ] AC2", "[x] AC2")
                self.assertEqual(plan(body, body, judgments)[0], expected)
                changed = body.replace(drift, "changed")
                self.assertNotEqual(digest(items), digest(from_issue_body(changed)))
                with self.assertRaises(KarteUsageError):
                    plan(body, changed, judgments)
                with self.assertRaises(KarteUsageError):
                    plan(body, body, judgments[:-1])
                if checks[-1].checked:
                    judgments[items.index(checks[-1])].result = "unverified"
                    with self.assertRaisesRegex(KarteUsageError, "オーナー判断"):
                        plan(body, body, judgments)

    def test_comment_only_text_is_hidden_but_visible_suffix_is_bound(self):
        body = FIRST + "<!-- first --> <!-- second -->\n- [x] AC2\n"
        self.assertEqual(from_issue_body(body)[0].text, "AC1")
        self.assertEqual(digest(from_issue_body(body)), digest(from_issue_body(body.replace("second", "other"))))
        body = FIRST + "<!-- note -->visible text\n- [x] AC2\n"
        self.assertIn("visible text", from_issue_body(body)[0].text)
        self.assertNotEqual(digest(from_issue_body(body)), digest(from_issue_body(body.replace("visible text", "changed"))))
