"""dsv2.cli — サブコマンドの終了コードと dry-run/apply の書込挙動。"""

import io
import unittest
from contextlib import redirect_stdout

from dsv2 import cli

from tests.unit.dsv2_fixtures import make_tree


class TestCli(unittest.TestCase):
    def setUp(self):
        self.root = make_tree(self)
        self.base = ["--root", str(self.root)]

    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main([*argv, *self.base])
        return code, buf.getvalue()

    def test_index_writes_meta(self):
        code, out = self._run(["index"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertTrue((self.root / "meta.json").exists())
        self.assertIn("索引化", out)

    def test_deps_and_unknown(self):
        code, out = self._run(["deps", "child-spec"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("parent-spec", out)
        code, _ = self._run(["deps", "nope"])
        self.assertEqual(code, cli.EXIT_NOT_FOUND)

    def test_dependents(self):
        code, out = self._run(["dependents", "parent-spec"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("child-spec", out)

    def test_orphans(self):
        code, out = self._run(["orphans"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("lonely", out)

    def test_drift_clean(self):
        code, out = self._run(["drift"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("ドリフトなし", out)

    def test_dashboard_outputs_markdown_snapshot(self):
        q_dir = self.root / "nodes/04-verification/q/open"
        q_dir.mkdir(parents=True, exist_ok=True)
        (q_dir / "owner-question.yaml").write_text(
            'title: "オーナー確認事項"\n'
            'version: "0.1.0"\n'
            "labels: []\n"
            'scheduled: "sprint-2"\n'
            "edges: []\n",
            encoding="utf-8",
        )
        code, out = self._run(["dashboard"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("# doc-system-v2 dashboard snapshot", out)
        self.assertIn("| `04-verification` |", out)
        self.assertIn("オーナー確認事項", out)
        self.assertIn("nodes/04-verification/q/open/owner-question.yaml", out)

    def test_reverse_dry_run_does_not_write(self):
        before = (self.root / "nodes/03-analysis/p/target-p.yaml").read_text("utf-8")
        code, out = self._run(["reverse", "fnd-open"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("dry-run", out)
        after = (self.root / "nodes/03-analysis/p/target-p.yaml").read_text("utf-8")
        self.assertEqual(before, after)
        self.assertTrue((self.root / "nodes/04-verification/fnd/open/fnd-open.yaml").exists())

    def test_reverse_apply_writes_and_moves(self):
        code, out = self._run(["reverse", "fnd-open", "--apply"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("適用済み", out)
        self.assertTrue((self.root / "nodes/04-verification/fnd/resolved/fnd-open.yaml").exists())
        self.assertIn('- to: "fnd-open"',
                      (self.root / "nodes/03-analysis/p/target-p.yaml").read_text("utf-8"))

    def test_reverse_unknown(self):
        code, _ = self._run(["reverse", "nope"])
        self.assertEqual(code, cli.EXIT_NOT_FOUND)

    def test_rename_dry_run_then_apply(self):
        code, out = self._run(["rename", "parent-spec", "parent-spec-v2"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("dry-run", out)
        self.assertTrue((self.root / "nodes/02-what/spec/parent-spec.yaml").exists())

        code, out = self._run(["rename", "parent-spec", "parent-spec-v2", "--apply"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn("適用済み", out)
        self.assertTrue((self.root / "nodes/02-what/spec/parent-spec-v2.yaml").exists())

    def test_rename_collision(self):
        code, _ = self._run(["rename", "parent-spec", "child-spec"])
        self.assertEqual(code, cli.EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()
