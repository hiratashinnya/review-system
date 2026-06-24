"""docidx.scan — Markdown 走査・本文抽出・trace_scope。"""

import tempfile
import unittest
from pathlib import Path

from docidx import scan

FIXTURE = """\
# 機能仕様

> ファイル説明（ノードではない）。

---

## SPEC-1: ノード埋め込みのパース（normal）

<details><summary>⬡ SPEC-1 · v0.3.0</summary>

```yaml
id: SPEC-1
type: SPEC
labels: []
scheduled: ""
condition: normal
edges:
  - to: FR-1
    ref_version: "0.3"
```
</details>

本文の一行目。
**例**: 本文に `⬡ SPEC-1 · v0.3.0` や ```yaml のような例が現れても誤検出しない。

---

## SPEC-2: 二つ目（boundary）

<details><summary>⬡ SPEC-2 · v0.1.0</summary>

```yaml
id: SPEC-2
type: SPEC
condition: boundary
labels: [post-mvp]
edges:
  - to: SPEC-1
    ref_version: "0.3"
```
</details>

二つ目の本文。
"""


class TestParseMarkdown(unittest.TestCase):
    def setUp(self):
        self.nodes = scan.parse_markdown(FIXTURE, "doc-system/sample.md")
        self.by_id = {n.id: n for n in self.nodes}

    def test_finds_exactly_two_nodes(self):
        # 本文中の例 ``⬡ SPEC-1`` を誤ってノード化しない
        self.assertEqual(len(self.nodes), 2)
        self.assertEqual(sorted(self.by_id), ["SPEC-1", "SPEC-2"])

    def test_heading_and_version_and_line(self):
        n = self.by_id["SPEC-1"]
        self.assertEqual(n.version, "0.3.0")
        self.assertTrue(n.heading.startswith("SPEC-1: ノード埋め込み"))
        self.assertEqual(n.type, "SPEC")
        self.assertEqual(n.condition, "normal")

    def test_edges_parsed(self):
        n = self.by_id["SPEC-1"]
        self.assertEqual(len(n.edges), 1)
        self.assertEqual(n.edges[0].to, "FR-1")
        self.assertEqual(n.edges[0].ref_version, "0.3")

    def test_labels_and_body(self):
        n = self.by_id["SPEC-2"]
        self.assertEqual(n.labels, ("post-mvp",))
        self.assertIn("二つ目の本文", n.body)
        # 本文は次ノードへ漏れない
        self.assertNotIn("SPEC-1", n.body)

    def test_no_parse_errors(self):
        self.assertTrue(all(n.parse_error is None for n in self.nodes))


class TestTraceScope(unittest.TestCase):
    def test_include_exclude(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc-system" / "02-what").mkdir(parents=True)
            (root / "doc-system" / "02-what" / "01-fr.md").write_text(FIXTURE, encoding="utf-8")
            (root / "doc-system" / "README.md").write_text("# readme\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "note.md").write_text("# excluded\n", encoding="utf-8")

            include = ["doc-system/**/*.md"]
            exclude = ["docs/**", "**/README.md"]
            files = scan.discover_files(root, include, exclude)
            rels = sorted(p.relative_to(root).as_posix() for p in files)
            self.assertEqual(rels, ["doc-system/02-what/01-fr.md"])

    def _write_config(self, root: Path, body: str) -> Path:
        cfg = root / "config.yaml"
        cfg.write_text(body, encoding="utf-8")
        return cfg

    def test_build_index_on_temp_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc-system").mkdir()
            (root / "doc-system" / "spec.md").write_text(FIXTURE, encoding="utf-8")
            cfg = self._write_config(
                root,
                'trace_scope:\n  include: ["doc-system/**/*.md"]\n  exclude: []\n',
            )
            index = scan.build_index(repo_root=root, config_path=cfg)
            self.assertEqual(len(index.nodes), 2)
            self.assertIn("SPEC-1", index.by_id)

    def test_inline_form_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self._write_config(
                root,
                'trace_scope:\n'
                '  include: ["doc-system/**/*.md"]\n'
                '  exclude: ["docs/**"]   # trailing comment\n',
            )
            include, exclude = scan.load_trace_scope(cfg)
            self.assertEqual(include, ["doc-system/**/*.md"])
            self.assertEqual(exclude, ["docs/**"])

    def test_exclude_optional_defaults_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self._write_config(root, 'trace_scope:\n  include: ["doc-system/**/*.md"]\n')
            include, exclude = scan.load_trace_scope(cfg)
            self.assertEqual(include, ["doc-system/**/*.md"])
            self.assertEqual(exclude, [])

    def test_missing_config_raises_not_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(scan.TraceScopeError) as ctx:
                scan.load_trace_scope(Path(tmp) / "missing.yaml")
            self.assertIn("見つかりません", str(ctx.exception))

    def test_block_form_raises_with_inline_hint(self):
        # ブロックリスト（- item）形式は黙って既定値に逃がさず停止し、記法を案内する
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self._write_config(
                root,
                "trace_scope:\n  include:\n    - doc-system/**/*.md\n",
            )
            with self.assertRaises(scan.TraceScopeError) as ctx:
                scan.load_trace_scope(cfg)
            msg = str(ctx.exception)
            self.assertIn("インラインリスト形式", msg)
            self.assertIn("include", msg)

    def test_no_trace_scope_block_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self._write_config(root, "current_phase: sprint-1\n")
            with self.assertRaises(scan.TraceScopeError) as ctx:
                scan.load_trace_scope(cfg)
            self.assertIn("trace_scope", str(ctx.exception))

    def test_include_missing_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self._write_config(root, 'trace_scope:\n  exclude: ["docs/**"]\n')
            with self.assertRaises(scan.TraceScopeError) as ctx:
                scan.load_trace_scope(cfg)
            self.assertIn("include", str(ctx.exception))


class TestMalformedYamlIsFailSoft(unittest.TestCase):
    def test_bad_block_records_parse_error_not_crash(self):
        bad = (
            "## X-1: 壊れた\n\n"
            "<details><summary>⬡ X-1 · v0.1.0</summary>\n\n"
            "```yaml\n"
            "id X-1\n"  # コロン無し → NodeYamlError
            "```\n"
            "</details>\n\n"
            "本文\n"
        )
        nodes = scan.parse_markdown(bad, "doc-system/x.md")
        self.assertEqual(len(nodes), 1)
        self.assertIsNotNone(nodes[0].parse_error)
        self.assertEqual(nodes[0].id, "X-1")  # バッジからは取れる


if __name__ == "__main__":
    unittest.main()
