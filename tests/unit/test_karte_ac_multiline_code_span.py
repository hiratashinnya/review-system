"""An inline Markdown code span may cross physical lines; do not hide following ACs."""
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

OPTIONS = dict(run_id="run-multiline", target_key="pr-846", phase="implementation",
               snapshot_oid="a" * 40, input_digest="b" * 64)
TICK = chr(96)
BODY = ("## Acceptance criteria\n- [ ] AC1 " + TICK + "literal\n"
        "foo <!--\n## Notes\n- [ ] not an AC\nbar" + TICK + "\n- [ ] AC2\n")


def decisions():
    return [SimpleNamespace(number=i, result="satisfied") for i in (1, 2)]


class MultilineCodeSpanTest(unittest.TestCase):
    def test_multiline_code_is_literal_and_real_ac2_is_visible(self):
        items = from_issue_body(BODY)
        self.assertEqual(2, len(items))
        self.assertEqual(["AC1 " + TICK + "literal", "AC2"],
                         [item.text.split("\n")[0] for item in items])
        self.assertIn("foo <!--", items[0].text)
        self.assertIn("## Notes", items[0].text)
        self.assertIn("- [ ] not an AC", items[0].text)
        self.assertEqual([False, False], [item.checked for item in items])
        drift = BODY.replace("- [ ] AC2", "- [ ] AC2 revised")
        self.assertNotEqual(digest(items), digest(from_issue_body(drift)))
        with self.assertRaisesRegex(KarteUsageError, "live本文"):
            plan(BODY, drift, decisions())
        updated, changed = plan(BODY, BODY, decisions())
        self.assertEqual([1, 2], changed)
        self.assertIn("- [ ] not an AC", updated)

    def test_code_span_delimiter_width_and_unclosed_tick(self):
        body = ("## Acceptance criteria\n- [ ] AC1 " + TICK * 2 + "literal\n"
                "foo " + TICK + " <!--\nbar" + TICK * 2 + "\n- [ ] AC2\n")
        self.assertEqual(2, len(from_issue_body(body)))
        stray = ("## Acceptance criteria\n- [ ] AC1 unmatched " + TICK +
                 " <!-- hidden -->\n- [ ] AC2\n")
        self.assertEqual(2, len(from_issue_body(stray)))

    @staticmethod
    def cli(handler, root, **kwargs):
        args = argparse.Namespace(repo_root=str(root), **kwargs)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return handler(args)

    def test_real_ingest_rejects_live_drift_before_mock_api_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tmp" / "_handoff").mkdir(parents=True)
            source = root / "tmp" / "issue.md"
            source.write_text(BODY, encoding="utf-8")
            identity = {"host": "github.com", "repository": "hiratashinnya/review-system"}
            with patch("karte.ac_repository.checkout_origin", return_value=identity):
                self.assertEqual(EXIT_OK, self.cli(owner_cli.cmd_activate, root, issue="801",
                                  ac_snapshot_file=str(source), repair_declared_scope=False, **OPTIONS))
                report = ("## Review Summary\n\n### Summary\nfinding_count: 0\nac_count: 2\n"
                          f"ac_snapshot_digest: {digest(from_issue_body(BODY))}\n"
                          "\n### AC 1\nresult: satisfied\nevidence: tested\nfinding_refs: []\n"
                          "\n### AC 2\nresult: satisfied\nevidence: tested\nfinding_refs: []\n"
                          "<!-- review-complete -->\n")
                expect = review_envelope.expected_of(issue=801, **OPTIONS)
                handoff = root / "tmp" / "_handoff" / "pr-reviewer--multiline.md"
                handoff.write_text(handoff_header.render_header(1, expect) + "\n" + report,
                                   encoding="utf-8")
                self.assertEqual(EXIT_OK, self.cli(reviewer_cli.cmd_ingest_reviewer, root,
                                  source=str(handoff), issue=None, round=None))
                receipt = model.parse(paths.read_text(paths.karte_path(801, root))).review_rounds[0]
                calls = []
                live = BODY.replace("- [ ] AC2", "- [ ] AC2 revised")
                def remote(host, repository, issue, *, new_body=None):
                    calls.append((host, repository, issue, new_body))
                    return live
                with self.assertRaisesRegex(KarteUsageError, "live本文"):
                    ac_owner_update.perform(root, 801, 1, receipt.ac_source,
                                            identity["repository"], remote=remote)
                self.assertTrue(calls)
                self.assertFalse(any(new_body is not None for *_, new_body in calls))


if __name__ == "__main__":
    unittest.main()
