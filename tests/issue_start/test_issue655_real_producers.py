"""Issue #822: the real harness producers create safe, detectable outputs."""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codex_worktree_exec.source_snapshot import verify_untracked_sources
from codex_worktree_exec.untracked_recovery import main as recover
from tests.unit.codex_worktree_exec_support import make_repository


class RealProducerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.source, self.target = make_repository(self.tmp)
        self.preserved = self.tmp / "preserved"
        self.preserved.mkdir()

    def fix(self):
        self.assertEqual(recover(["--worktree", str(self.source), "--apply",
                                  "--quarantine-parent", str(self.preserved)]), 0)
        verify_untracked_sources(self.source)

    def test_gitgate_show_pr_diff_actual_cli_generates_diff_then_recovers(self):
        from gitgate.dispatch import main
        blob = b"diff --git a/file b/file\n" + b"x" * 5000
        result = subprocess.CompletedProcess([], 0, blob, b"")
        cwd = Path.cwd()
        stream = io.StringIO()
        try:
            os.chdir(self.source)
            with patch("gitgate.pr_diff.subprocess.run", return_value=result) as runner:
                with contextlib.redirect_stdout(stream):
                    self.assertEqual(main(["show-pr-diff", "822"]), 0)
            runner.assert_called_once()
        finally:
            os.chdir(cwd)
        data = json.loads(stream.getvalue())
        self.assertEqual((self.source / data["path"]).read_bytes(), blob)
        with self.assertRaisesRegex(ValueError, "unapproved_tmp"):
            verify_untracked_sources(self.source)
        self.fix()
        self.assertEqual(len(list(self.preserved.glob(
            "review-system-quarantine-*/tmp/pr-diffs/*.diff"))), 1)

    def test_adr_new_entry_actual_cli_generates_root_notice_then_recovers(self):
        from adr.cli import main
        from adr.schema import ADR_SPEC
        from feedback_ledger.tomlwrite import dumps
        from tests.unit.test_adr import draft
        (self.source / "adr").mkdir()
        data = draft("dummy822")
        data["source"][0]["issue"] = 822
        proposal = self.tmp / "draft.toml"
        proposal.write_text(dumps(ADR_SPEC, data))
        directory = self.tmp / "adr-store"
        directory.mkdir()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["new-entry", "--root", str(directory),
                                   "--repo", str(self.source), "--draft", str(proposal)]), 0)
        self.assertIn("ADR-WRITE-ROOT:", output.getvalue())
        self.assertTrue(list((self.source / "tmp/_adr-notify").glob("*.root")))
        with self.assertRaisesRegex(ValueError, "unapproved_tmp"):
            verify_untracked_sources(self.source)
        self.fix()

    def test_karte_append_actual_cli_generates_allowed_pointer_and_lock(self):
        from tests.unit.karte_support import finding, report_text, run_cli
        report = self.source / "tmp/review.md"
        report.parent.mkdir()
        report.write_text(report_text(
            ("new", finding("pkg/file.py::foo", "dummy safe issue 822"))))
        result = run_cli(self.source, ["ingest-review", "--issue", "822",
                                      "--round", "1", "--from", str(report)])
        self.assertEqual(result[0], 0, result[2])
        result = run_cli(self.source, [
            "append", "--issue", "822", "--round", "1",
            "--finding-ids", "F-822-01", "--root-cause", "dummy-trace",
            "--change-kind", "logic", "--targets", "pkg/file.py::foo",
            "--diagnosis", "isolated harmless fixture",
        ])
        self.assertEqual(result[0], 0, result[2])
        self.assertTrue((self.source / "tmp/_karte/issue-822.md").exists())
        self.assertTrue((self.source / "tmp/_karte/.writer.lock").exists())
        verify_untracked_sources(self.source)
