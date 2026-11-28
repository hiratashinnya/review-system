"""Escaped HTML comment openings remain visible and bound to AC digests."""
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
from karte.errors import KarteUsageError
from karte.exit_codes import EXIT_OK

OPTIONS = dict(run_id="run-escaped", target_key="pr-846", phase="implementation",
               snapshot_oid="a" * 40, input_digest="b" * 64)
BODY = "## Acceptance criteria\n- [ ] AC1 \\<!-- must authenticate -->\n- [x] AC2\n"


def satisfied():
    return [SimpleNamespace(number=i, result="satisfied") for i in (1, 2)]


class EscapedCommentTest(unittest.TestCase):
    def test_escaped_opener_is_part_of_reviewed_ac(self):
        ac = from_issue_body(BODY)
        self.assertEqual([False, True], [item.checked for item in ac])
        self.assertIn("must authenticate", ac[0].text)
        edited = BODY.replace("must authenticate", "must authorize")
        self.assertNotEqual(digest(ac), digest(from_issue_body(edited)))
        with self.assertRaisesRegex(KarteUsageError, "live本文"):
            plan(BODY, edited, satisfied())
        updated, changes = plan(BODY, BODY, satisfied())
        self.assertEqual([1], changes)
        self.assertIn("- [x] AC1 \\<!-- must authenticate -->", updated)

    def test_escape_parity_and_escaped_backtick(self):
        for count in (1, 2, 3, 4):
            with self.subTest(backslashes=count):
                body = ("## Acceptance criteria\n- [ ] AC1 " + "\\" * count
                        + "<!-- hidden text -->\n- [ ] AC2\n")
                ac = from_issue_body(body)
                self.assertEqual(2, len(ac))
                self.assertEqual(count % 2 == 1, "hidden text" in ac[0].text)
        body = ("## Acceptance criteria\n- [ ] AC1 \\" + chr(96)
                + "literal <!-- hidden -->" + chr(96) + "\n- [ ] AC2\n")
        ac = from_issue_body(body)
        self.assertEqual(2, len(ac))
        self.assertNotIn("hidden", ac[0].text)

    @staticmethod
    def cli(fn, root, **fields):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return fn(argparse.Namespace(repo_root=str(root), **fields))

    def test_accepted_round_refuses_live_drift_before_github_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tmp" / "_handoff").mkdir(parents=True)
            src = root / "tmp" / "issue.md"
            src.write_text(BODY, encoding="utf-8")
            origin = {"host": "github.com", "repository": "hiratashinnya/review-system"}
            with patch("karte.ac_repository.checkout_origin", return_value=origin):
                self.assertEqual(EXIT_OK, self.cli(owner_cli.cmd_activate, root, issue="801",
                    ac_snapshot_file=str(src), repair_declared_scope=False, **OPTIONS))
                report = ("## Review Summary\n\n### Summary\nfinding_count: 0\nac_count: 2\n"
                          f"ac_snapshot_digest: {digest(from_issue_body(BODY))}\n"
                          "\n### AC 1\nresult: satisfied\nevidence: tested\nfinding_refs: []\n"
                          "\n### AC 2\nresult: satisfied\nevidence: tested\nfinding_refs: []\n"
                          "<!-- review-complete -->\n")
                expected = review_envelope.expected_of(issue=801, **OPTIONS)
                handoff = root / "tmp" / "_handoff" / "pr-reviewer--escaped.md"
                handoff.write_text(handoff_header.render_header(1, expected) + "\n" + report,
                                   encoding="utf-8")
                self.assertEqual(EXIT_OK, self.cli(reviewer_cli.cmd_ingest_reviewer, root,
                    source=str(handoff), issue=None, round=None))
                receipt = model.parse(paths.read_text(paths.karte_path(801, root))).review_rounds[0]
                calls = []
                edited = BODY.replace("must authenticate", "must authorize")
                def remote(host, repository, issue, *, new_body=None):
                    calls.append(new_body)
                    return edited
                with self.assertRaisesRegex(KarteUsageError, "live本文"):
                    ac_owner_update.perform(root, 801, 1, receipt.ac_source,
                                            origin["repository"], remote=remote)
                self.assertEqual([None], calls)


if __name__ == "__main__":
    unittest.main()
