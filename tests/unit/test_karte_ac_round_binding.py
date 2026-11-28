"""Real activate -> cancellation -> ingest must bind the accepted AC source."""
import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karte import ac_owner_update, handoff_header, model, owner_cli, paths, review_envelope, reviewer_cli
from karte.active_pointer import read_active
from karte.ac_snapshot import digest, from_issue_body

OPTIONS = dict(run_id="run-B", target_key="pr-846", phase="implementation",
               snapshot_oid="a" * 40, input_digest="b" * 64)
ISSUE_B = "# Issue B\n\n## Acceptance criteria\n- [ ] AC1\n"
ISSUE_A = ISSUE_B.replace("Issue B", "Issue A")


class AcceptedACBindingTest(unittest.TestCase):
    def call(self, handler, root, **fields):
        args = argparse.Namespace(repo_root=str(root), **fields)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return handler(args)

    def test_cancelled_source_cannot_write_after_another_origin_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tmp" / "_handoff").mkdir(parents=True)
            src = root / "tmp" / "issue.md"
            origin_b = {"host": "git-b.corp.example", "repository": "owner/project-b"}
            origin_a = {"host": "github.com", "repository": "owner/project-a"}
            with patch("karte.ac_repository.checkout_origin", return_value=origin_b):
                src.write_text(ISSUE_B, encoding="utf-8")
                self.assertEqual(0, self.call(owner_cli.cmd_activate, root, issue="801",
                                  ac_snapshot_file=str(src), repair_declared_scope=False, **OPTIONS))
                old = read_active(root, required=True)["ac_snapshot"]
                self.assertEqual(0, self.call(owner_cli.cmd_activate, root, issue="801",
                                  repair_declared_scope=False))
            with patch("karte.ac_repository.checkout_origin", return_value=origin_a):
                src.write_text(ISSUE_A, encoding="utf-8")
                new_options = {**OPTIONS, "run_id": "run-A"}
                self.assertEqual(0, self.call(owner_cli.cmd_activate, root, issue="801",
                                  ac_snapshot_file=str(src), repair_declared_scope=False, **new_options))
                current = read_active(root, required=True)["ac_snapshot"]
                self.assertNotEqual(old["source"], current["source"])
                report = ("## Review Summary\n\n### Summary\nfinding_count: 0\nac_count: 1\n"
                          f"ac_snapshot_digest: {digest(from_issue_body(ISSUE_A))}\n\n"
                          "### AC 1\nresult: satisfied\nevidence: tested\nfinding_refs: []\n"
                          "<!-- review-complete -->\n")
                expected = review_envelope.expected_of(issue=801, **new_options)
                handoff = root / "tmp" / "_handoff" / "pr-reviewer--accepted.md"
                handoff.write_text(handoff_header.render_header(1, expected) + "\n" + report,
                                   encoding="utf-8")
                self.assertEqual(0, self.call(reviewer_cli.cmd_ingest_reviewer, root,
                                  source=str(handoff), issue=None, round=None))
                record = model.parse(paths.read_text(paths.karte_path(801, root))).review_rounds[0]
                self.assertEqual((current["source"], origin_a["host"], origin_a["repository"]),
                                 (record.ac_source, record.ac_host, record.ac_repository))
            calls = []
            live = [ISSUE_A]
            def remote(host, repository, issue, *, new_body=None):
                calls.append((host, repository, issue, new_body is not None))
                if new_body is not None:
                    live[0] = new_body
                return live[0]
            with patch("karte.ac_repository.checkout_origin", return_value=origin_b):
                with self.assertRaisesRegex(Exception, "受理済みround"):
                    ac_owner_update.perform(root, 801, 1, old["source"], origin_b["repository"],
                                            remote=remote)
            self.assertEqual([], calls)
            with patch("karte.ac_repository.checkout_origin", return_value=origin_a):
                with self.assertRaisesRegex(Exception, "受理済みround"):
                    ac_owner_update.perform(root, 801, 1, old["source"], origin_a["repository"],
                                            remote=remote)
                self.assertEqual([], calls)
                self.assertEqual([1], ac_owner_update.perform(
                    root, 801, 1, current["source"], origin_a["repository"], remote=remote))
            self.assertEqual(1, sum(is_write for *_, is_write in calls))
            self.assertIn("- [x] AC1", live[0])


if __name__ == "__main__":
    unittest.main()
