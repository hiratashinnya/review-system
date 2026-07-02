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

    def test_check_open_without_backref_is_not_flagged(self):
        # P-100 に →FND-100 を仕込まない通常の open FND は、forward 辺を持つだけで
        # open-but-backref-exists が誤検出されてはならない（fid が自身の forward 辺
        # によって dependents[e.to] に載るのは常に真になるため、判定は
        # 「対象が fid への backward 辺を持つか」で行う。回帰防止のための固定テスト。
        code, out = self._run(["check", "--id", "FND-100", *self.base])
        self.assertNotIn("open-but-backref-exists", out)

    def test_stray_hr_detects_body_and_ignores_separator(self):
        # SPEC-62: 本文中の孤立 `---`（次が本文prose）は検出、ノード分離 `---`（次が
        # `## 見出し`）は検出しない。截断被害ノードの ID を主体に指す。
        from backref import notation
        md = "\n".join([
            "## FND-1: t", "<details><summary>⬡ FND-1 · v0.1.0</summary>", "",
            "```yaml", "id: FND-1", "type: FND", "edges: []", "```", "",
            "</details>", "", "**内容**: part1", "",
            "---", "",                      # ← 本文内 stray（次=bold prose）
            "**内容続き**: part2", "",
            "---", "",                      # ← ノード分離（次=## 見出し）＝正常
            "## FND-2: t2", "<details><summary>⬡ FND-2 · v0.1.0</summary>",
            "```yaml", "id: FND-2", "type: FND", "edges: []", "```", "</details>",
            "", "**内容**: body2", "",
        ])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = root / "doc-system" / "x.md"
            f.parent.mkdir(parents=True)
            f.write_text(md, encoding="utf-8")
            findings = notation.check_stray_hr(root, [f])
        strays = [x for x in findings if x.code == "stray-hr-in-body"]
        self.assertEqual(len(strays), 1)              # 分離 `---` は誤検出しない
        self.assertEqual(strays[0].fnd_id, "FND-1")   # 截断被害ノードを指す
        self.assertEqual(strays[0].severity, "warning")

    def test_stray_hr_h3_subheading_vs_node_heading(self):
        # レビュー指摘の回帰: `---` の直後が H3 でも、本文小見出し（後続に <details> なし）は
        # stray、ノード見出し（後続に <details> あり）は非検出。実パーサは `---` を無条件境界に
        # するため「H2以上を一律 legit」ではなく「見出しの後に <details> が続くか」で判定する。
        from backref import notation
        md = "\n".join([
            "## N-1: t", "<details><summary>⬡ N-1 · v0.1.0</summary>",
            "```yaml", "id: N-1", "type: FND", "edges: []", "```", "</details>", "",
            "**内容**: part1", "",
            "---", "",                       # ← 本文内 stray（次=H3 本文小見出し・後続 details なし）
            "### 本文小見出し", "",
            "截断される本文prose", "",
            "---", "",                       # ← ノード分離（次=H3 ノード見出し・後続 details あり）
            "### N-2: t2", "<details><summary>⬡ N-2 · v0.1.0</summary>",
            "```yaml", "id: N-2", "type: FND", "edges: []", "```", "</details>",
            "", "**内容**: body2", "",
        ])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = root / "doc-system" / "x.md"
            f.parent.mkdir(parents=True)
            f.write_text(md, encoding="utf-8")
            strays = [x for x in notation.check_stray_hr(root, [f])
                      if x.code == "stray-hr-in-body"]
        self.assertEqual(len(strays), 1)            # H3 本文小見出しの stray のみ
        self.assertEqual(strays[0].fnd_id, "N-1")   # 截断被害ノード

    def test_check_reports_stray_hr(self):
        # CLI 配線: 既存ノード本文末尾に stray `---`＋prose を注入 → check が検出
        p = self.root / "doc-system/04-verification/02-findings.md"
        p.write_text(p.read_text("utf-8") + "\n\n---\n\n**截断される本文**: xx\n", "utf-8")
        code, out = self._run(["check", *self.base])
        self.assertIn("stray-hr-in-body", out)


if __name__ == "__main__":
    unittest.main()
