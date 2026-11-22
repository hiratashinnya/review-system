"""HTML comments cannot become AC headings, review judgments, or owner writes."""
import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from karte import ac_owner_update, handoff_header, model, owner_cli, paths, review_envelope, reviewer_cli
from karte.ac_check_update import plan
from karte.ac_snapshot import digest, from_issue_body
from karte.exit_codes import EXIT_OK

OPTIONS = dict(run_id="run-html", target_key="pr-846", phase="implementation",
               snapshot_oid="a" * 40, input_digest="b" * 64)
BODY = (
    "# Issue\n<!--\n## Acceptance criteria\n- [ ] pseudo before AC\n-->\n"
    "## Acceptance criteria\n"
    "- [ ] AC1 <!-- private note -->\n"
    "<!--\n## Notes\n- [ ] hidden checkbox\n-->\n"
    "- [ ] AC2\n"
    "<!--\n## Acceptance criteria\n- [ ] pseudo after AC\n-->\n"
    "## Notes\n- [ ] unrelated\n"
)


def decisions(count):
    return [SimpleNamespace(number=i, result="satisfied") for i in range(1, count + 1)]


class HTMLCommentACBindingTest(unittest.TestCase):
    def test_hidden_headings_and_checkboxes_do_not_change_ac_digest(self):
        ac = from_issue_body(BODY)
        self.assertEqual(["AC1", "AC2"], [item.text for item in ac])
        self.assertEqual([False, False], [item.checked for item in ac])
        self.assertEqual([7, 12], [item.line_number for item in ac])
        hidden_only = BODY.replace("hidden checkbox", "different hidden checkbox")
        self.assertEqual(digest(ac), digest(from_issue_body(hidden_only)))
        self.assertNotEqual(digest(ac), digest(from_issue_body(BODY.replace("AC2\n", "AC2 changed\n"))))
        updated, changed = plan(BODY, BODY, decisions(2))
        self.assertEqual([1, 2], changed)
        self.assertIn("- [x] AC1 <!-- private note -->", updated)
        self.assertIn("- [x] AC2", updated)
        self.assertIn("- [ ] hidden checkbox", updated)
        self.assertIn("- [ ] pseudo before AC", updated)
        self.assertIn("- [ ] pseudo after AC", updated)
        self.assertIn("- [ ] unrelated", updated)

    def test_fenced_literal_and_inline_code_comment_markers(self):
        fence = chr(96) * 3
        body = ("## Acceptance criteria\n- [ ] AC1\n"
                + fence + "markdown\n<!--\n## Notes\n- [ ] literal in code\n"
                + fence + "\n<!--\n## Notes\n-->\n"
                "- [ ] AC2 " + chr(96) + "<!-- literal -->" + chr(96)
                + " <!-- actual comment -->\n")
        items = from_issue_body(body)
        self.assertEqual(2, len(items))
        self.assertIn("literal in code", items[0].text)
        self.assertEqual("AC2 " + chr(96) + "<!-- literal -->" + chr(96), items[1].text)
        updated, changed = plan(body, body, decisions(2))
        self.assertEqual([1, 2], changed)
        self.assertIn("- [ ] literal in code", updated)
        self.assertIn("- [x] AC2", updated)

    @staticmethod
    def cli(handler, root, **kwargs):
        args = argparse.Namespace(repo_root=str(root), **kwargs)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return handler(args)

    def test_end_to_end_review_and_mock_ac_write_ignore_html_comment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tmp" / "_handoff").mkdir(parents=True)
            src = root / "tmp" / "issue.md"
            src.write_text(BODY, encoding="utf-8")
            origin = {"host": "github.com", "repository": "hiratashinnya/review-system"}
            with patch("karte.ac_repository.checkout_origin", return_value=origin):
                self.assertEqual(EXIT_OK, self.cli(
                    owner_cli.cmd_activate, root, issue="801", ac_snapshot_file=str(src),
                    repair_declared_scope=False, **OPTIONS))
                report = ("## Review Summary\n\n### Summary\nfinding_count: 0\nac_count: 2\n"
                          f"ac_snapshot_digest: {digest(from_issue_body(BODY))}\n"
                          "\n### AC 1\nresult: satisfied\nevidence: tested\nfinding_refs: []\n"
                          "\n### AC 2\nresult: satisfied\nevidence: tested\nfinding_refs: []\n"
                          "<!-- review-complete -->\n")
                expect = review_envelope.expected_of(issue=801, **OPTIONS)
                handoff = root / "tmp" / "_handoff" / "pr-reviewer--html.md"
                handoff.write_text(handoff_header.render_header(1, expect) + "\n" + report,
                                   encoding="utf-8")
                self.assertEqual(EXIT_OK, self.cli(
                    reviewer_cli.cmd_ingest_reviewer, root, source=str(handoff),
                    issue=None, round=None))
                ledger = model.parse(paths.read_text(paths.karte_path(801, root)))
                self.assertEqual(1, len(ledger.review_rounds))
                frozen = ledger.review_rounds[0]
                remote_body = [BODY]
                calls = []
                def mock_remote(host, repository, issue, *, new_body=None):
                    calls.append((host, repository, issue, new_body is not None))
                    if new_body is not None:
                        remote_body[0] = new_body
                    return remote_body[0]
                self.assertEqual([1, 2], ac_owner_update.perform(
                    root, 801, 1, frozen.ac_source, origin["repository"], remote=mock_remote))
                self.assertEqual(1, sum(write for _, _, _, write in calls))
                self.assertIn("- [x] AC2", remote_body[0])
                self.assertIn("- [ ] hidden checkbox", remote_body[0])
                self.assertIn("- [ ] pseudo before AC", remote_body[0])
                self.assertIn("- [ ] pseudo after AC", remote_body[0])


if __name__ == "__main__":
    unittest.main()
