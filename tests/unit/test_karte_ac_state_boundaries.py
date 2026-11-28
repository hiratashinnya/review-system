"""N5/N6: retain comments and terminate fenced/inline state at list boundaries."""
import unittest
from types import SimpleNamespace

from karte.ac_snapshot import from_issue_body, digest
from karte.ac_check_update import plan
from karte.errors import KarteUsageError

FIRST = "## Acceptance criteria\n- [ ] AC1"


def boundary_cases():
    for checked in (" ", "x"):
        last = f"- [{checked}] AC2\n"
        for fake in ("- [ ] example only", "## Notes"):
            for gap in ("", "\n"):
                yield (FIRST + "\n" + gap + "<!-- first --> <!-- second\n" + fake
                       + "\n-->\n\n" + last), ["AC1", "AC2"], "AC2"
        for marker in ("```", "~~~"):
            for indent in (2, 4):
                for end in ("", " " * indent + marker + "\n"):
                    yield (FIRST + "\n" + " " * indent + marker + "\n"
                           + " " * indent + "example\n" + end + last), ["AC1", "AC2"], "AC2"
        for gap in ("", "\n"):
            for tail in ("", " -->"):
                yield (FIRST + " <!-- note\n" + gap + last.rstrip("\n") + tail + "\n"), ["AC1", "AC2"], "AC2"
        for indent in (1, 2, 3):
            first = FIRST.replace("- [ ]", "-   [ ]") if indent > 1 else FIRST
            yield first + "\n" + " " * indent + last, ["AC1", "AC2"], "AC2"
        for marker in ("```", "~~~"):
            for indent in range(2, 6):
                prefix = " " * indent
                fence = f"{prefix}{marker}md\n{prefix}-->\n{prefix}{marker}\n"
                yield FIRST + " <!-- note\n" + fence + last, ["AC1", "AC2"], "note"
        for block in ("  <div>\n  -->\n  </div>\n", "  <!-- inner\n  -->\n", "  * * *\n  -->\n"):
            yield FIRST + " <!-- note\n" + block + last, ["AC1", "AC2"], "note"
        yield FIRST + " <!-- note\n  hidden -->\n" + last, ["AC1", "AC2"], "AC2"
        yield FIRST + " <!-- note\nlazy --> suffix\n" + last, ["AC1", "AC2"], "suffix"
        yield FIRST + " <!-- note -->\n" + last, ["AC1", "AC2"], "AC2"
        yield FIRST + "\n<!-- first -->visible <!-- second\nexample\n-->\n" + last, ["AC1", "AC2"], "visible"
        for example in ("    ```markdown\n", "    <pre>\n"):
            end = "    ```\n" if example.endswith("markdown\n") else "    </pre>\n"
            usage = "- Usage\n" + example + "  ## Acceptance criteria\n  - [ ] example only\n" + end
            yield usage + "\n" + FIRST + "\n" + last, ["AC1", "AC2"], "AC2"


class StateBoundaryTest(unittest.TestCase):
    def test_heading_under_padded_list_indent_ends_section(self):
        body = "## Acceptance criteria\n-   Plain AC1\n  ## Notes\n- [ ] Unrelated\n"
        self.assertEqual([(i.text, i.checked) for i in from_issue_body(body)], [("Plain AC1", None)])
        self.assertEqual(plan(body, body, [SimpleNamespace(number=1, result="satisfied")]), (body, []))

    def test_boundaries_preserve_full_coverage_and_write_positions(self):
        for body, names, drift in boundary_cases():
            with self.subTest(body=body):
                items = from_issue_body(body)
                self.assertEqual([i.text.split()[0] for i in items], names)
                self.assertEqual(len(items), 2)
                self.assertEqual([i.checked for i in items], [False, "- [x] AC2" in body])
                decisions = [SimpleNamespace(number=n, result="satisfied") for n in (1, 2)]
                expected = body.replace("[ ] AC1", "[x] AC1").replace("[ ] AC2", "[x] AC2")
                self.assertEqual(plan(body, body, decisions)[0], expected)
                live = body.replace(drift, "changed")
                self.assertNotEqual(digest(items), digest(from_issue_body(live)))
                with self.assertRaises(KarteUsageError):
                    plan(body, live, decisions)
                with self.assertRaises(KarteUsageError):
                    plan(body, body, decisions[:1])
                if items[-1].checked:
                    decisions[-1].result = "not_met"
                    with self.assertRaisesRegex(KarteUsageError, "オーナー判断"):
                        plan(body, body, decisions)

    def test_inline_and_block_text_contract(self):
        literal = FIRST + " <!-- unclosed note\n- [x] AC2\n"
        self.assertIn("<!-- unclosed note", from_issue_body(literal)[0].text)
        hidden = FIRST + " <!-- note\n  private -->\n- [x] AC2\n"
        self.assertEqual(from_issue_body(hidden)[0].text, "AC1")
        self.assertEqual(digest(from_issue_body(hidden)), digest(from_issue_body(hidden.replace("private", "other"))))
        lazy = FIRST + " <!-- note\nlazy --> suffix\n- [x] AC2\n"
        self.assertEqual(from_issue_body(lazy)[0].text, "AC1\n suffix")
        self.assertEqual(digest(from_issue_body(lazy)), digest(from_issue_body(lazy.replace("lazy", "other"))))
        suffix = FIRST + "\n<!-- first -->visible <!-- second\nexample\n-->\n- [x] AC2\n"
        self.assertIn("visible", from_issue_body(suffix)[0].text)
        self.assertNotIn("example", from_issue_body(suffix)[0].text)
