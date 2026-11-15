"""既存の参照系 verb は origin と GitHub から独立する。"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from karte import finding_handoff_github, finding_handoff_origin, model
from tests.unit.karte_support import run_cli
from tests.unit.test_karte_finding_handoff_predicate import verified_item


class OfflineVerbTest(unittest.TestCase):
    def test_status_render_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = model.new_karte(7)
            ledger.findings = [verified_item()]
            ledger.attempts = [model.Attempt(1, 1, ["F-7-01"], "same-cause", "logic", ["a.py"], "診断")]
            ledger.results = [model.Result(1, ["F-7-01"], ["a.py"], "partial", "一部")]
            path = root / "tmp/_karte/issue-7.md"
            path.parent.mkdir(parents=True)
            path.write_text(model.dumps(ledger), encoding="utf-8")
            with patch.object(finding_handoff_origin, "get_origin", side_effect=AssertionError("origin")), \
                 patch.object(finding_handoff_github, "get_issue", side_effect=AssertionError("gh")), \
                 patch.object(finding_handoff_github, "list_comments", side_effect=AssertionError("gh")), \
                 patch.object(finding_handoff_github, "get_comment", side_effect=AssertionError("gh")), \
                 patch.object(finding_handoff_github, "post_comment", side_effect=AssertionError("gh")), \
                 patch.object(finding_handoff_github, "current_login", side_effect=AssertionError("gh")), \
                 patch("subprocess.run", side_effect=AssertionError("実コマンド禁止")):
                for argv in (["status", "--issue", "7"], ["render", "--issue", "7"],
                             ["check", "--issue", "7", "--round", "1"]):
                    with self.subTest(argv=argv):
                        code, _, error = run_cli(root, argv)
                        self.assertEqual(0, code, error)
