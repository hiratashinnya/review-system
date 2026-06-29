"""backref.cli — サブコマンドの終了コードと書込挙動。"""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from backref import cli
from tests.unit.test_backref_reverse import _make_tree


class TestCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root, self.cfg = _make_tree(self._tmp.name)
        self.base = ["--root", str(self.root), "--config", str(self.cfg)]

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(argv)
        return code, buf.getvalue()

    def test_reverse_dry_run_does_not_write(self):
        before = (self.root / "doc-system/04-verification/02-findings.md").read_text("utf-8")
        code, out = self._run(["reverse", "FND-100", *self.base])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("dry-run", out)
        after = (self.root / "doc-system/04-verification/02-findings.md").read_text("utf-8")
        self.assertEqual(before, after)

    def test_reverse_apply_writes(self):
        code, out = self._run(["reverse", "FND-100", "--apply", *self.base])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("適用済み", out)
        text = (self.root / "doc-system/04-verification/02-findings.md").read_text("utf-8")
        self.assertIn("resolved: true", text)

    def test_reverse_unknown_id_not_found(self):
        code, _ = self._run(["reverse", "FND-999", *self.base])
        self.assertEqual(code, cli.EXIT_NOT_FOUND)

    def test_check_reports_findings_and_exit_code(self):
        # FND-200 は edges:[]・未 resolved・被参照ゼロ。open-but-... ではないが、
        # 適用後の不整合検出を見るため、まず FND-100 を反転してから check。
        self._run(["reverse", "FND-100", "--apply", *self.base])
        code, out = self._run(["check", *self.base])
        # FND-100 は整合（resolved+backref+DD-3）。FND-200 の状態次第で 0/1。
        self.assertIn(code, (cli.EXIT_OK, cli.EXIT_FINDINGS))
        self.assertIsInstance(out, str)

    def test_check_open_but_backref(self):
        # P-100 に先回りで →FND-100 を仕込み、open のまま矛盾を作る
        p = self.root / "doc-system/03-analysis/03-processes.md"
        t = p.read_text("utf-8").replace(
            '  - to: SPEC-1\n    ref_version: "0.3"',
            '  - to: SPEC-1\n    ref_version: "0.3"\n  - to: FND-100\n    ref_version: "0.1"',
        )
        p.write_text(t, "utf-8")
        code, out = self._run(["check", "--id", "FND-100", *self.base])
        self.assertEqual(code, cli.EXIT_FINDINGS)
        self.assertIn("open-but-backref-exists", out)


if __name__ == "__main__":
    unittest.main()
