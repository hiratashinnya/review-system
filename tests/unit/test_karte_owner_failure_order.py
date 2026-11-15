"""主文脈の scope 決定はマーカー保存に成功してから台帳を更新する。"""

import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from karte import owner_cli, owner_decision, scope_ledger
from karte.exit_codes import EXIT_ERROR


class OwnerFailureOrderTest(unittest.TestCase):
    def test_marker_failure_leaves_ledger_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledger.md"
            ledger.write_text("before", encoding="utf-8")
            args = argparse.Namespace(repo_root=str(root), issue="375", finding="F-375-01",
                                      disposition=None, deferred_to=None, waived_by=None,
                                      waived_reason=None, scope="out")
            karte = mock.Mock()
            karte.findings = []
            with mock.patch.object(owner_cli, "load_karte", return_value=(ledger, karte)), \
                 mock.patch.object(owner_decision, "record_decision", return_value=["scope: out"]), \
                 mock.patch.object(scope_ledger, "record_owner", side_effect=OSError("marker disk full")), \
                 mock.patch.object(owner_decision, "write_karte") as write, \
                 contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(EXIT_ERROR, owner_cli.cmd_decide(args))
            self.assertIn("marker disk full", err.getvalue())
            write.assert_not_called()
            self.assertEqual("before", ledger.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
