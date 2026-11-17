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

    def test_envelope_without_snapshot_stops_before_pointer_write(self):
        code, _, err = self.run_cli(owner_cli.cmd_activate, issue="801",
                                    repair_declared_scope=False, **OPTIONS)
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("snapshot必須", err)
        self.assertFalse((self.root / "tmp" / "_karte" / "active.json").exists())

    def test_legacy_mode_cannot_accept_zero_finding_summary(self):
        code, _, err = self.run_cli(owner_cli.cmd_activate, issue="801",
                                    legacy_finding_only=True, repair_declared_scope=False, **OPTIONS)
        self.assertEqual(code, EXIT_OK, err)
        self.assertEqual(self.ingest(self.make_report())[0], EXIT_ERROR)
        self.assertFalse(paths.karte_path(801, self.root).exists())

    def test_zero_findings_accepts_and_persists(self):
        self.assertEqual(self.activate()[0], EXIT_OK)
        code, _, err = self.ingest(self.make_report())
        self.assertEqual(code, EXIT_OK, err)
        ledger = model.parse(paths.read_text(paths.karte_path(801, self.root)))
        self.assertEqual(ledger.findings, [])
        self.assertEqual(ledger.review_rounds[0].number, 1)
        from karte.scope_records import exists, ledger_path
        self.assertTrue(exists(801, self.root))
        self.assertEqual(ledger_path(801, self.root).read_text(encoding="utf-8").strip(), "")
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

    def make_unmet_report(self, *, result="unverified", status="open"):
        status_line = "" if status is None else f"status: {status}\n"
        return (
            "## Findings\n\n### new\n"
            "harm: real\nharm_detail: ACの必須試験が未実施のため動作を確認できない\n"
            "severity: major\nscope: in\nlocus: tests/integration\n"
            "summary: AC1の実環境動作が未検証\n"
            "evidence: 実環境の試験結果が存在しない\n"
            "expected: 実環境で動作が確認される\n"
            "recheck: 実環境で必要な試験を実行する\n" + status_line +
            "\n## Review Summary\n\n### Summary\n"
            "finding_count: 1\nac_count: 2\nac_snapshot_digest: " +
            digest(from_issue_body(BODY)) + "\n\n"
            "### AC 1\nresult: " + result +
            "\nevidence: AC1の実環境試験が未実施\nfinding_refs: [new@1]\n\n"
            "### AC 2\nresult: satisfied\nevidence: AC2の単体試験が成功\nfinding_refs: []\n"
            "<!-- review-complete -->\n"
        )

    def test_codex_resolved_ac_reference_rejected_without_mutation(self):
        from karte.active_pointer import read_active
        for result in ("not_met", "unverified"):
            with self.subTest(result=result):
                self.assertEqual(self.activate()[0], EXIT_OK)
                original_pointer = read_active(self.root, required=True)
                code, _, err = self.ingest(
                    self.make_unmet_report(result=result, status="resolved"),
                    f"pr-reviewer--resolved-{result}.md",
                )
                self.assertEqual(code, EXIT_ERROR, err)
                self.assertIn("status: open", err)
                self.assertFalse(paths.karte_path(801, self.root).exists())
                self.assertEqual(original_pointer, read_active(self.root, required=True))
                self.assertFalse((self.root / "tmp" / "_karte" /
                                  "issue-801-review-round-1.md").exists())

    def test_open_and_default_status_keep_unmet_ac_out_of_clean(self):
        from karte.status_payload import status_payload
        for status in ("open", None):
            with self.subTest(status=status):
                # Each successful ingestion advances the round: use a fresh sandbox.
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / "tmp" / "_handoff").mkdir(parents=True)
                    source = root / "tmp" / "issue.md"
                    source.write_text(BODY, encoding="utf-8")
                    previous_root, previous_source = self.root, self.source
                    try:
                        self.root, self.source = root, source
                        self.assertEqual(self.activate()[0], EXIT_OK)
                        code, _, err = self.ingest(
                            self.make_unmet_report(status=status),
                            f"pr-reviewer--open-{status or 'default'}.md",
                        )
                        self.assertEqual(code, EXIT_OK, err)
                        ledger = model.parse(paths.read_text(paths.karte_path(801, root)))
                        self.assertEqual(ledger.findings[0].status, "open")
                        self.assertEqual(status_payload(ledger)["verdict"], "harmful-open")
                        self.assertEqual([1], [r.number for r in ledger.review_rounds])
                    finally:
                        self.root, self.source = previous_root, previous_source

    def test_closed_hash_and_setext_headings_require_ac_judgment_at_ingest(self):
        for heading in ("## Acceptance criteria ##", "## 受け入れ基準 ##",
                        "Acceptance criteria\n-------------------", "受け入れ基準\n-----------"):
            with self.subTest(heading=heading):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / "tmp" / "_handoff").mkdir(parents=True)
                    source = root / "tmp" / "issue.md"
                    body = heading + "\n- [ ] real condition\n"
                    source.write_text(body, encoding="utf-8")
                    old_root, old_source = self.root, self.source
                    try:
                        self.root, self.source = root, source
                        ac = from_issue_body(body)
                        self.assertEqual(len(ac), 1)
                        self.assertEqual(self.activate()[0], EXIT_OK)
                        bad, _, _ = self.ingest(
                            self.make_report(count=0, digest_value=digest(ac)),
                            "pr-reviewer--bad-closed-hash.md",
                        )
                        self.assertEqual(bad, EXIT_ERROR)
                        self.assertFalse(paths.karte_path(801, root).exists())
                        good, _, err = self.ingest(
                            self.make_report(count=1, digest_value=digest(ac)),
                            "pr-reviewer--valid-closed-hash.md",
                        )
                        self.assertEqual(good, EXIT_OK, err)
                        self.assertEqual(len(model.parse(paths.read_text(
                            paths.karte_path(801, root))).review_rounds), 1)
                    finally:
                        self.root, self.source = old_root, old_source

    def test_prose_ac_requires_full_summary_and_never_autochecks(self):
        from karte.ac_check_update import plan
        from karte.review_summary_ac import ACJudgment

        prose = ("# Example\n\n## Acceptance criteria\n"
                 "実環境での動作確認に成功すること。\n")
        self.source.write_text(prose, encoding="utf-8")
        criteria = from_issue_body(prose)
        self.assertEqual(len(criteria), 1)
        self.assertEqual(criteria[0].checked, None)
        self.assertEqual(self.activate()[0], EXIT_OK)
        code, _, err = self.ingest(
            self.make_report(count=0, digest_value=digest(criteria)),
            "pr-reviewer--invalid-prose-zero.md",
        )
        self.assertEqual(code, EXIT_ERROR, err)
        self.assertFalse(paths.karte_path(801, self.root).exists())
        code, _, err = self.ingest(
            self.make_report(count=1, digest_value=digest(criteria)),
            "pr-reviewer--valid-prose-one.md",
        )
        self.assertEqual(code, EXIT_OK, err)
        ledger = model.parse(paths.read_text(paths.karte_path(801, self.root)))
        self.assertEqual(len(ledger.review_rounds), 1)
        report = paths.read_text(self.root / ledger.review_rounds[0].source)
        self.assertIn("### AC 1", report)
        judgments = (ACJudgment(1, "satisfied", "証拠", ()),)
        self.assertEqual(plan(prose, prose, judgments), (prose, []))

    def test_no_pointer_and_replayed_handoff_fail(self):
        report = self.make_report()
        self.assertEqual(self.ingest(report)[0], EXIT_ERROR)
        self.activate()
        self.assertEqual(self.ingest(report)[0], EXIT_OK)
        self.assertEqual(self.ingest(report)[0], EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()
