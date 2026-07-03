"""dsv2.migrate — v1 → v2 一括移行の契約（代表ケース・stdlib のみ）。

小さな v1 スタイルのコーパス（doc-system/**/*.md）を一時ディレクトリに作り、
migrate の純関数と end-to-end run を検証する。slug 生成は doc-system-v2/slugify.py を使う。
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dsv2 import migrate


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _badge(nid: str, ver: str, yaml_body: str) -> str:
    return (f"<details><summary>⬡ {nid} · v{ver}</summary>\n\n"
            f"```yaml\n{yaml_body}\n```\n</details>\n")


class TestStripTitle(unittest.TestCase):
    def test_strips_condition_suffix(self):
        self.assertEqual(migrate.strip_title_markers("ノード埋め込みのパース（normal）"),
                         "ノード埋め込みのパース")

    def test_strips_composite_condition_and_label(self):
        self.assertEqual(migrate.strip_title_markers("傘 SPEC（normal・アンブレラ）"), "傘 SPEC")
        self.assertEqual(migrate.strip_title_markers("題（normal・post-mvp）"), "題")

    def test_strips_umbrella_marker(self):
        self.assertEqual(migrate.strip_title_markers("ノードフォーマットスキーマ（傘）"),
                         "ノードフォーマットスキーマ")

    def test_keeps_meaningful_trailing_parens(self):
        self.assertEqual(migrate.strip_title_markers("図からの逆起こし（往復）"),
                         "図からの逆起こし（往復）")


class TestUmbrella(unittest.TestCase):
    def test_normal_umbrella_detected(self):
        ids = {"spec": {"SPEC-1", "SPEC-1-1"}}
        parent = {"id": "SPEC-1", "type": "spec", "condition": "normal"}
        child = {"id": "SPEC-1-1", "type": "spec", "condition": "normal"}
        self.assertTrue(migrate.is_umbrella_normal(parent, ids))
        self.assertFalse(migrate.is_umbrella_normal(child, ids))

    def test_non_normal_parent_not_umbrella(self):
        # 異常系の親（condition:error）は #71 規則7 の傘定義に該当せず condition を保持。
        ids = {"spec": {"SPEC-2", "SPEC-2-1"}}
        parent = {"id": "SPEC-2", "type": "spec", "condition": "error"}
        self.assertFalse(migrate.is_umbrella_normal(parent, ids))


class TestAssignSlugs(unittest.TestCase):
    def test_collision_resolved_by_type_suffix(self):
        nodes = [
            {"id": "I-5", "type": "i", "title": "config.yaml"},
            {"id": "DS-2", "type": "ds", "title": "config.yaml"},
        ]
        m = migrate.assign_slugs(nodes)
        self.assertEqual(m["I-5"], "config.yaml-i")
        self.assertEqual(m["DS-2"], "config.yaml-ds")
        # slug == slugify(更新後 title) を保つ。
        from slugify import slugify
        for n in nodes:
            self.assertEqual(m[n["id"]], slugify(n["title"]))

    def test_same_type_collision_escalates_to_id_suffix(self):
        nodes = [
            {"id": "P-1-4", "type": "p", "title": "スキーマ検証"},
            {"id": "P-5-2", "type": "p", "title": "スキーマ検証"},
        ]
        m = migrate.assign_slugs(nodes)
        self.assertNotEqual(m["P-1-4"], m["P-5-2"])
        self.assertIn("p-1-4", m["P-1-4"])
        self.assertIn("p-5-2", m["P-5-2"])

    def test_no_collision_keeps_base(self):
        nodes = [{"id": "VAL-1", "type": "val", "title": "トレーサビリティ"}]
        self.assertEqual(migrate.assign_slugs(nodes)["VAL-1"], "トレーサビリティ")


class TestBuildEdges(unittest.TestCase):
    def _ctx(self):
        id2slug = {"P-2": "p2-slug", "P-2-1": "p21-slug", "SPEC-1": "s1"}
        id2node = {"P-2": {"id": "P-2", "version": "0.4.0"},
                   "P-2-1": {"id": "P-2-1", "version": "0.1.0"}}
        return id2slug, id2node

    def test_rewrites_to_and_synthesizes_parent(self):
        id2slug, id2node = self._ctx()
        node = {"id": "P-2-1", "edges": [{"to": "SPEC-1", "ref_version": "0.3"}]}
        counters = {"synth": 0, "dangling": []}
        out = migrate.build_edges(node, id2slug, id2node, counters)
        tos = {e["to"] for e in out}
        self.assertIn("s1", tos)          # 旧 id → slug 張替え
        self.assertIn("p2-slug", tos)     # 親 P-2 への合成辺
        self.assertEqual(counters["synth"], 1)
        synth = next(e for e in out if e["to"] == "p2-slug")
        self.assertEqual(synth["ref_version"], "0.4")  # 親 x.y

    def test_no_duplicate_parent_edge(self):
        id2slug, id2node = self._ctx()
        node = {"id": "P-2-1", "edges": [{"to": "P-2", "ref_version": "0.4"}]}
        counters = {"synth": 0, "dangling": []}
        out = migrate.build_edges(node, id2slug, id2node, counters)
        self.assertEqual(counters["synth"], 0)  # 既存辺があるので合成しない
        self.assertEqual([e["to"] for e in out], ["p2-slug"])

    def test_dangling_recorded(self):
        id2slug, id2node = self._ctx()
        node = {"id": "SPEC-1", "edges": [{"to": "GHOST", "ref_version": "0.1"}]}
        counters = {"synth": 0, "dangling": []}
        out = migrate.build_edges(node, id2slug, id2node, counters)
        self.assertEqual(out, [])
        self.assertEqual(counters["dangling"], [("SPEC-1", "GHOST")])


class TestSerialize(unittest.TestCase):
    def test_drops_condition_for_umbrella_and_includes_suppress(self):
        node = {"id": "V-1", "type": "verify", "title": 'タイ"トル無し', "version": "0.1.2",
                "condition": None, "labels": [], "scheduled": "",
                "suppress": ["RULE-004"], "suppress_reason": "凍結免除",
                "carrier": None, "result": None, "log_ref": None}
        node["title"] = "検証記録"
        y = migrate.serialize_sidecar(node, [{"to": "x", "ref_version": "0.2"}], drop_condition=False)
        self.assertIn("suppress: [RULE-004]", y)
        self.assertIn("suppress_reason:", y)
        # docidx.nodeyaml で往復読取できる。
        from docidx import nodeyaml
        data = nodeyaml.parse(y)
        self.assertEqual(data["suppress"], ["RULE-004"])
        self.assertEqual(data["edges"][0]["to"], "x")

    def test_umbrella_drops_condition(self):
        node = {"id": "S-1", "type": "spec", "title": "傘", "version": "0.1.0",
                "condition": "normal", "labels": [], "scheduled": "",
                "suppress": [], "suppress_reason": None, "carrier": None,
                "result": None, "log_ref": None}
        y = migrate.serialize_sidecar(node, [], drop_condition=True)
        self.assertNotIn("condition:", y)


class TestEndToEnd(unittest.TestCase):
    def _corpus(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        src = base / "doc-system"
        # SPEC 親（normal・アンブレラ）＋子（failure・親へ辺）
        _write(src, "02-what/03-spec.md",
               "# spec\n\n---\n\n"
               "## SPEC-1: 傘（normal・アンブレラ）\n\n"
               + _badge("SPEC-1", "0.3.0",
                        "id: SPEC-1\ntype: SPEC\nlabels: []\nscheduled: \"\"\ncondition: normal\nedges:\n  - to: FR-1\n    ref_version: \"0.3\"")
               + "\n傘の本文。\n\n---\n\n"
               "## SPEC-1-1: 子の判定（normal）\n\n"
               + _badge("SPEC-1-1", "0.1.0",
                        "id: SPEC-1-1\ntype: SPEC\nlabels: []\nscheduled: \"\"\ncondition: normal\nedges:\n  - to: SPEC-1\n    ref_version: \"0.3\"")
               + "\n子の本文。\n\n---\n")
        _write(src, "02-what/01-fr.md",
               "# fr\n\n---\n\n## FR-1: 機能要求\n\n"
               + _badge("FR-1", "0.3.0", "id: FR-1\ntype: FR\nlabels: []\nscheduled: \"\"\nedges: []")
               + "\nFR 本文。\n\n---\n")
        # 除外対象ファイル（無視されること）
        _write(src, "00-dashboard.md", "## X-1: これは対象外\n")
        return src, base

    def test_run_produces_pairs_and_paths(self):
        src, base = self._corpus()
        dst = base / "doc-system-v2"
        stats = migrate.run(src, dst)
        self.assertEqual(stats["nodes"], 3)          # SPEC-1, SPEC-1-1, FR-1（dashboard 除外）
        self.assertEqual(stats["dangling"], 0)
        # 傘 SPEC-1（normal＋同型子）は condition 落とし。
        self.assertEqual(stats["umbrella_dropped"], 1)
        # 配置: FR は 02-what/fr、SPEC は 02-what/spec。
        self.assertTrue((dst / "nodes" / "02-what" / "fr").is_dir())
        specs = list((dst / "nodes" / "02-what" / "spec").glob("*.yaml"))
        self.assertEqual(len(specs), 2)
        # レポート生成。
        self.assertTrue((dst / "MIGRATION_REPORT.md").exists())

    def test_run_is_idempotent(self):
        src, base = self._corpus()
        dst = base / "doc-system-v2"
        migrate.run(src, dst)
        stats2 = migrate.run(src, dst)
        self.assertEqual(stats2["nodes"], 3)
        pairs = list((dst / "nodes").rglob("*.yaml"))
        self.assertEqual(len(pairs), 3)  # 二重生成されない


if __name__ == "__main__":
    unittest.main()
