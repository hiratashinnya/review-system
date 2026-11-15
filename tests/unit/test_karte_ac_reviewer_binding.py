"""Issue #801: 実際の ingest-reviewer 経路でAC snapshotを束縛する。"""

import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from karte import handoff_header, model, owner_cli, paths, review_envelope, reviewer_cli
from karte.ac_snapshot import digest, from_issue_body
from karte.exit_codes import EXIT_ERROR, EXIT_OK

OPTIONS = dict(run_id="run-801", target_key="pr-846", phase="implementation",
               snapshot_oid="a" * 40, input_digest="b" * 64)
BODY = "# Issue\n\n## Acceptance criteria\n- [ ] AC1\n- [ ] AC2\n"


class ACReviewerBindingTest(unittest.TestCase):
    def setUp(self):
        self.ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.ctx.cleanup)
        self.root = Path(self.ctx.name)
        (self.root / "tmp" / "_handoff").mkdir(parents=True)
        self.source = self.root / "tmp" / "issue.md"
        self.source.write_text(BODY, encoding="utf-8")

    def run_cli(self, fn, **options):
        out, err = io.StringIO(), io.StringIO()
        args = argparse.Namespace(repo_root=str(self.root), **options)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = fn(args)
        return code, out.getvalue(), err.getvalue()

    def activate(self):
        return self.run_cli(owner_cli.cmd_activate, issue="801", ac_snapshot_file=str(self.source),
                            repair_declared_scope=False, **OPTIONS)

    def make_report(self, *, count=2, digest_value=None, complete=True):
        digest_value = digest_value or digest(from_issue_body(BODY))
        result = ("## Review Summary\n\n### Summary\n"
                  "finding_count: 0\nac_count: " + str(count) +
                  "\nac_snapshot_digest: " + digest_value + "\n")
        for index in range(1, count + 1):
            result += ("\n### AC " + str(index) +
                       "\nresult: satisfied\nevidence: 実行済み\nfinding_refs: []\n")
        if complete:
            result += "<!-- review-complete -->\n"
        return result

    def ingest(self, report, name="pr-reviewer--review801.md"):
        expected = review_envelope.expected_of(issue=801, **OPTIONS)
        source = self.root / "tmp" / "_handoff" / name
        source.write_text(handoff_header.render_header(1, expected) + "\n" + report, encoding="utf-8")
        return self.run_cli(reviewer_cli.cmd_ingest_reviewer, source=str(source), issue=None, round=None)

    def test_zero_findings_accepts_and_persists(self):
        self.assertEqual(self.activate()[0], EXIT_OK)
        code, _, err = self.ingest(self.make_report())
        self.assertEqual(code, EXIT_OK, err)
        ledger = model.parse(paths.read_text(paths.karte_path(801, self.root)))
        self.assertEqual(ledger.findings, [])
        self.assertEqual(ledger.review_rounds[0].number, 1)
        archived = self.root / ledger.review_rounds[0].source
        self.assertIn("Review Summary", archived.read_text(encoding="utf-8"))

    def test_missing_truncated_and_mismatched_summary_are_rejected(self):
        cases = ["", "## Findings\n", self.make_report(complete=False),
                 self.make_report(count=1), self.make_report(digest_value="c" * 64)]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                self.assertEqual(self.activate()[0], EXIT_OK)
                code, _, _ = self.ingest(case, f"pr-reviewer--bad{index}.md")
                self.assertEqual(code, EXIT_ERROR)
                self.assertFalse(paths.karte_path(801, self.root).exists())

    def test_no_pointer_and_replayed_handoff_fail(self):
        report = self.make_report()
        self.assertEqual(self.ingest(report)[0], EXIT_ERROR)
        self.activate()
        self.assertEqual(self.ingest(report)[0], EXIT_OK)
        self.assertEqual(self.ingest(report)[0], EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()
