"""asset_parity.cli — サブコマンド `check` の出力形式と終了コード。"""

import io
import json
import unittest
from contextlib import redirect_stdout

from asset_parity import cli

from tests.unit.asset_parity_fixtures import make_tree


class TestCliCheck(unittest.TestCase):
    def setUp(self):
        self.root = make_tree(self)

    def _run(self, extra_args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["check", "--root", str(self.root), *extra_args])
        return code, buf.getvalue()

    def test_text_format_exits_drift_when_missing_present(self):
        code, out = self._run(["--format", "text"])
        self.assertEqual(code, cli.EXIT_DRIFT)  # fixture has missing-everywhere-skill etc.
        self.assertIn("MISSING", out)
        self.assertIn("plain-skill", out)

    def test_json_format_is_valid_json_with_summary(self):
        code, out = self._run(["--format", "json"])
        payload = json.loads(out)
        self.assertIn("summary", payload)
        self.assertIn("assets", payload)
        self.assertEqual(code, cli.EXIT_DRIFT)

    def test_both_format_prints_text_then_json(self):
        code, out = self._run(["--format", "both"])
        self.assertIn("asset_parity", out)
        # text は波括弧を含まないため、最初の `{` が JSON ブロックの開始。
        brace = out.index("{")
        json.loads(out[brace:])

    def test_usage_error_exit_code(self):
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(buf):
                cli.main(["not-a-command"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
