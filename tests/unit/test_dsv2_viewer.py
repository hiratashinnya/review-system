"""dsv2.viewer — doc_view.html 生成器の契約（合成 meta からの生成・データ反映・オフライン性）。"""

import json
import re
import unittest
from pathlib import Path

from dsv2 import meta, viewer

from tests.unit.dsv2_fixtures import make_tree

_DATA_RE = re.compile(
    r'<script type="application/json" id="data">(.*?)</script>', re.S
)


def _embedded(html: str) -> dict:
    """生成 HTML に埋め込まれた JSON データを取り出す（``<\\/`` エスケープを戻す）。"""
    m = _DATA_RE.search(html)
    assert m, "埋め込み JSON が見つからない"
    return json.loads(m.group(1).replace("<\\/", "</"))


class TestMarkdown(unittest.TestCase):
    def test_heading_and_paragraph(self):
        h = viewer.render_markdown("# 見出し\n\n段落テキスト。")
        self.assertIn("<h1>見出し</h1>", h)
        self.assertIn("<p>段落テキスト。</p>", h)

    def test_inline_code_not_decorated(self):
        h = viewer.render_markdown("これは `**not bold**` です。")
        self.assertIn("<code>**not bold**</code>", h)
        self.assertNotIn("<strong>", h)

    def test_bold_and_link(self):
        h = viewer.render_markdown("**強調** と [リンク](https://x.example)。")
        self.assertIn("<strong>強調</strong>", h)
        self.assertIn('<a href="https://x.example"', h)

    def test_list_and_fence(self):
        h = viewer.render_markdown("- a\n- b\n\n```\nx=1\n```")
        self.assertIn("<ul><li>a</li><li>b</li></ul>", h)
        self.assertIn("<pre><code>x=1</code></pre>", h)

    def test_html_escaped(self):
        h = viewer.render_markdown("a < b & c > d")
        self.assertIn("&lt;", h)
        self.assertIn("&amp;", h)
        self.assertNotIn("<b ", h)


class TestViewer(unittest.TestCase):
    def setUp(self):
        self.root = make_tree(self)
        self.meta = meta.build_meta(self.root)

    def _build(self, out_name="doc_view.html") -> str:
        out = self.root / out_name
        viewer.build_view(self.root, self.meta, out)
        return out.read_text(encoding="utf-8")

    def test_contains_all_node_ids(self):
        html = self._build()
        data = _embedded(html)
        ids = {n["id"] for n in data["nodes"]}
        self.assertEqual(
            ids,
            {"parent-spec", "child-spec", "target-p", "fnd-open", "lonely"},
        )

    def test_edges_carried_into_data(self):
        data = _embedded(self._build())
        child = next(n for n in data["nodes"] if n["id"] == "child-spec")
        self.assertEqual([d["to"] for d in child["deps"]], ["parent-spec"])
        parent = next(n for n in data["nodes"] if n["id"] == "parent-spec")
        self.assertIn("child-spec", [d["from"] for d in parent["dependents"]])

    def test_no_drift_marker_when_consistent(self):
        html = self._build()
        # 一貫している合成ツリーではドリフト辺 0（ヘッダ表示も 0）。
        data = _embedded(html)
        drift_edges = [d for n in data["nodes"] for d in n["deps"] if d["drift"]]
        self.assertEqual(drift_edges, [])
        self.assertIn("ドリフト辺 <b>0</b>", html)

    def test_drift_reflected_after_data_change(self):
        # child-spec の ref を 0.9 にして親 0.1 とドリフトさせ、再生成に反映されること。
        for n in self.meta["nodes"]:
            if n["id"] == "child-spec":
                n["edges"][0]["ref_version"] = "0.9"
        html = self._build()
        data = _embedded(html)
        child = next(n for n in data["nodes"] if n["id"] == "child-spec")
        self.assertTrue(child["deps"][0]["drift"])
        self.assertIn('<span class="badge drift">', html)
        self.assertIn("ドリフト辺 <b>1</b>", html)

    def test_drift_matches_query(self):
        # ビューアのドリフト集計は dsv2.query.drift と一致する（CLI と同一ロジック）。
        from dsv2 import query
        for n in self.meta["nodes"]:
            if n["id"] == "child-spec":
                n["edges"][0]["ref_version"] = "0.9"
        model = viewer.build_view_model(self.root, self.meta)
        view_drift = sum(1 for n in model["nodes"] for d in n["deps"] if d["drift"])
        self.assertEqual(view_drift, len(query.drift(self.meta)))

    def test_body_rendered_to_html(self):
        data = _embedded(self._build())
        parent = next(n for n in data["nodes"] if n["id"] == "parent-spec")
        self.assertIn("<p>", parent["body_html"])

    def test_regeneration_reflects_body_change(self):
        html1 = self._build()
        self.assertNotIn("NEWLY-ADDED-MARKER", html1)
        body = self.root / "nodes/02-what/spec/parent-spec.md"
        body.write_text("NEWLY-ADDED-MARKER の本文。\n", encoding="utf-8")
        html2 = self._build()
        self.assertIn("NEWLY-ADDED-MARKER", html2)

    def test_no_external_network_refs(self):
        """オフライン自己完結＝*ロードされる*外部リソースが無いこと。本文アンカーの
        ``https://`` リンクはロードしないので許容する（実コーパスは URL を多数含む）。"""
        html = self._build()
        for pat in (
            "<script src=", "<link ", 'src="http', "src='http",
            'src="//', "src='//", "@import", "//cdn",
        ):
            self.assertNotIn(pat, html)

    def test_external_anchor_link_allowed(self):
        """本文中の外部リンクはアンカー化されるが、外部ロードは発生しない。"""
        body = self.root / "nodes/02-what/spec/parent-spec.md"
        body.write_text("参照: [site](https://example.com/x)\n", encoding="utf-8")
        html = self._build()
        node = next(n for n in _embedded(html)["nodes"] if n["id"] == "parent-spec")
        self.assertIn('href="https://example.com/x"', node["body_html"])
        self.assertNotIn("<script src=", html)

    def test_javascript_scheme_link_degraded(self):
        """``javascript:`` 等の危険スキームはリンク化せずテキストへ降格する。"""
        body = self.root / "nodes/02-what/spec/parent-spec.md"
        body.write_text("危険: [x](javascript:alert(1))\n", encoding="utf-8")
        html = self._build()
        node = next(n for n in _embedded(html)["nodes"] if n["id"] == "parent-spec")
        self.assertNotIn("<a ", node["body_html"])  # リンク化されない
        self.assertNotIn("javascript:", node["body_html"])  # スキームは href に載らない
        self.assertIn("x", node["body_html"])  # リンクテキストは残る

    def test_glob_star_not_italicized(self):
        """空白隣接の glob（``*.md`` ``*.py``）を <em> へ誤爆させない。"""
        h = viewer.render_markdown("生成物は *.md と *.py を対象にする")
        self.assertNotIn("<em>", h)

    def test_lonely_node_present(self):
        data = _embedded(self._build())
        lonely = next(n for n in data["nodes"] if n["id"] == "lonely")
        self.assertEqual(lonely["deps"], [])
        self.assertEqual(lonely["dependents"], [])


if __name__ == "__main__":
    unittest.main()
