"""新規 Issue の activate 後、主文脈が round を省略して取り込める。"""

import contextlib
import io
import json

from karte import exit_codes, owner_cli, paths
from tests.unit.karte_support import RootedCase, finding, ingest_argv, report_text, rooted_args


class IngestReviewAfterActivateTests(RootedCase):
    def test_activate_without_expectation_then_ingest_defaults_to_round_one(self):
        self.assertFalse((self.root / "tmp" / "_karte" / "issue-375.md").exists())
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = owner_cli.cmd_activate(rooted_args(self.root, issue="375"))
        self.assertEqual(exit_codes.EXIT_OK, code, err.getvalue())
        active = json.loads(paths.active_path(self.root).read_text(encoding="utf-8"))
        self.assertEqual({"issue": 375, "round": 0}, active)
        report = report_text(("new", finding("a.py::check", "検証が不足")))

        code, _out, err = self.run_verb(ingest_argv(), report)

        self.assertEqual(exit_codes.EXIT_OK, code, err)
        self.assertEqual([1], self.ledger(375).findings[0].rounds)
        active = json.loads(paths.active_path(self.root).read_text(encoding="utf-8"))
        self.assertEqual({"issue": 375, "round": 1}, active)
