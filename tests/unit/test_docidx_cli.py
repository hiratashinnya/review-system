"""docidx CLI / build_index の E2E（実物の doc-system ツリーに対して）。"""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from docidx import cli, scan

REPO_ROOT = Path(__file__).resolve().parents[2]

_SAMPLE_MD = """\
## SPEC-1: サンプル（normal）

<details><summary>⬡ SPEC-1 · v0.1</summary>

```yaml
id: SPEC-1
type: SPEC
condition: normal
```
</details>

本文。
"""


class TestRealTree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = scan.build_index(repo_root=REPO_ROOT)

    def test_parses_many_nodes_without_errors(self):
        self.assertGreater(len(self.index.nodes), 100)
        errs = [n for n in self.index.nodes if n.parse_error]
        self.assertEqual(errs, [], f"parse errors: {[(n.id, n.parse_error) for n in errs]}")

    def test_ids_unique_and_wellformed(self):
        import re
        ids = [n.id for n in self.index.nodes]
        self.assertEqual(len(ids), len(set(ids)), "重複 ID あり")
        bad = [i for i in ids if not re.fullmatch(r"[A-Z]+(-\d+)+", i)]
        self.assertEqual(bad, [])

    def test_fr1_present_with_edges(self):
        fr1 = self.index.by_id.get("FR-1")
        self.assertIsNotNone(fr1)
        self.assertEqual(fr1.type, "FR")
        self.assertTrue(fr1.edges)

    def test_spec_hierarchy_children_present(self):
        for nid in ("SPEC-1", "SPEC-1-1", "SPEC-1-2"):
            self.assertIn(nid, self.index.by_id)


class TestCliMain(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["--root", str(REPO_ROOT), *argv])
        return code, buf.getvalue()

    def test_index_json_is_valid(self):
        code, out = self._run(["index"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(any(n["id"] == "FR-1" for n in data))

    def test_show_json(self):
        code, out = self._run(["show", "FR-1"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data[0]["id"], "FR-1")
        self.assertIn("body", data[0])

    def test_show_missing_returns_2(self):
        code, _ = self._run(["show", "NOPE-999"])
        self.assertEqual(code, cli.EXIT_NOT_FOUND)

    def test_deps_json(self):
        code, out = self._run(["deps", "SPEC-1-1"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["id"], "SPEC-1-1")
        self.assertTrue(all("drift" in r for r in data["deps"]))

    def test_dependents_json(self):
        code, out = self._run(["dependents", "FR-1"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(len(data["dependents"]) > 0)

    def test_search_by_type(self):
        code, out = self._run(["search", "--type", "FND"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(all(n["type"] == "FND" for n in data))


class TestCliTraceScopeFailClose(unittest.TestCase):
    """必須1: trace_scope を読めない config は既定値に逃がさず EXIT_CONFIG で停止し警告する。"""

    def _run(self, root: Path, config: Path, argv):
        # 共通フラグはサブコマンドの後ろに置く（前置すると親パーサ既定で上書きされる）
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main([*argv, "--root", str(root), "--config", str(config)])
        return code, out.getvalue(), err.getvalue()

    def test_block_form_config_exits_config_with_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc-system").mkdir()
            (root / "doc-system" / "spec.md").write_text(_SAMPLE_MD, encoding="utf-8")
            cfg = root / "config.yaml"
            cfg.write_text("trace_scope:\n  include:\n    - doc-system/**/*.md\n", encoding="utf-8")
            code, _, err = self._run(root, cfg, ["index"])
            self.assertEqual(code, cli.EXIT_CONFIG)
            self.assertIn("インラインリスト形式", err)


class TestCliDuplicateWarning(unittest.TestCase):
    """必須2: ノード ID 重複は stderr に警告（全出現 file:line・先勝ち採用先）を出す。"""

    def _run(self, root: Path, config: Path, argv):
        # 共通フラグはサブコマンドの後ろに置く（前置すると親パーサ既定で上書きされる）
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main([*argv, "--root", str(root), "--config", str(config)])
        return code, out.getvalue(), err.getvalue()

    def test_duplicate_id_warns_but_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc-system").mkdir()
            (root / "doc-system" / "a.md").write_text(_SAMPLE_MD, encoding="utf-8")
            (root / "doc-system" / "b.md").write_text(_SAMPLE_MD, encoding="utf-8")  # 同じ SPEC-1
            cfg = root / "config.yaml"
            cfg.write_text('trace_scope:\n  include: ["doc-system/**/*.md"]\n', encoding="utf-8")
            code, out, err = self._run(root, cfg, ["index"])
            self.assertEqual(code, cli.EXIT_OK)  # read-only 情報ツールとして継続
            self.assertIn("ノード ID 重複 SPEC-1", err)
            self.assertIn("doc-system/a.md", err)
            self.assertIn("doc-system/b.md", err)


if __name__ == "__main__":
    unittest.main()
