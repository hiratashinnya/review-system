"""追加 verb の実エントリ登録と writer lock を検証する。"""

import contextlib
import io
import subprocess
import sys
from unittest import mock

from karte import cli, handoff_header, owner_cli, paths, review_envelope, reviewer_cli
from tests.unit.karte_support import (
    RootedCase, finding, karte_sandbox, report_text, verb_parsers, writer_lock_is_held,
)


REGISTRARS = (reviewer_cli.register, owner_cli.register)
ENVELOPE = {
    "run_id": "run-7", "target_key": "pr-7", "phase": "implementation",
    "snapshot_oid": "a" * 40, "input_digest": "b" * 64,
}
ENVELOPE_FLAGS = [
    "--run-id", "run-7", "--target-key", "pr-7", "--phase", "implementation",
    "--snapshot-oid", "a" * 40, "--input-digest", "b" * 64,
]


class TestOwnerReviewerEntry(RootedCase):
    def run_registered(self, argv):
        args = cli.build_parser(REGISTRARS).parse_args(argv)
        args.repo_root = str(self.root)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = args.func(args)
        return code, out.getvalue(), err.getvalue()

    def held_at_write(self, argv):
        observed = []
        original = paths.write_text_atomic

        def probe(*args, **kwargs):
            observed.append(writer_lock_is_held(self.root))
            return original(*args, **kwargs)

        with mock.patch.object(paths, "write_text_atomic", side_effect=probe):
            code, _, err = self.run_registered(argv)
        self.assertEqual(0, code, err)
        self.assertTrue(observed, "書き込みが観測されていない")
        self.assertTrue(all(observed), observed)

    def prepare_finding(self):
        self.assertEqual(0, self.run_registered(["activate", "--issue", "7", *ENVELOPE_FLAGS])[0])
        handoff = self.root / "tmp" / "_handoff" / "pr-reviewer--test.md"
        handoff.parent.mkdir(parents=True)
        handoff.write_text(
            handoff_header.render_header(1, review_envelope.expected_of(issue=7, **ENVELOPE)) + "\n\n"
            + report_text(("new", finding("a.py::f", "問題"))), encoding="utf-8"
        )
        return str(handoff)

    def test_subprocess_resolves_all_three_verbs(self):
        sandbox = karte_sandbox(self)
        for verb in ("ingest-reviewer", "decide", "activate"):
            with self.subTest(verb=verb):
                result = subprocess.run(
                    [sys.executable, "-m", "karte", verb, "--help"], cwd=sandbox,
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertIn(f"karte {verb}", result.stdout)

    def test_registered_verbs_declare_lock_requirement(self):
        locked = {"ingest-reviewer": True, "decide": True, "activate": True}
        parsers = verb_parsers(cli.build_parser(REGISTRARS))
        for verb, expected in locked.items():
            with self.subTest(verb=verb):
                self.assertIs(expected, parsers[verb].get_default("func").locked)

    def test_activate_writes_inside_lock(self):
        self.held_at_write(["activate", "--issue", "7"])

    def test_ingest_reviewer_writes_inside_lock(self):
        path = self.prepare_finding()
        self.held_at_write(["ingest-reviewer", "--from", path])

    def test_decide_writes_inside_lock(self):
        path = self.prepare_finding()
        self.assertEqual(0, self.run_registered(["ingest-reviewer", "--from", path])[0])
        self.held_at_write([
            "decide", "--issue", "7", "--finding", "F-7-01", "--scope", "out",
        ])
