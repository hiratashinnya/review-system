"""dsv2 テスト用の v2 サンプルツリー生成（一時 git リポジトリ）。

``nodes/**`` に「親 SPEC／子 SPEC（親へ辺）／プロセス P（backref 付与先）／open FND（P へ forward 辺）／
完全孤立ノード」を配置し、git init＋add まで済ませて返す。git mv を伴う reverse/rename を検証できる。
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _node(root: Path, rel_dir: str, slug: str, md: str, yaml: str) -> None:
    _w(root / "nodes" / rel_dir / f"{slug}.md", md)
    _w(root / "nodes" / rel_dir / f"{slug}.yaml", yaml)


def make_tree(test: unittest.TestCase) -> Path:
    """v2 サンプルツリーを一時ディレクトリに構築し root Path を返す（cleanup 登録済み）。"""
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    root = Path(tmp.name) / "doc-system-v2"
    root.mkdir(parents=True)

    _node(
        root, "02-what/spec", "parent-spec",
        "親（アンブレラ）SPEC の本文。\n",
        'title: "親 SPEC のタイトル"\nversion: "0.1.0"\nlabels: []\nscheduled: ""\nedges: []\n',
    )
    _node(
        root, "02-what/spec", "child-spec",
        "子 SPEC の本文。孤立 `---` 検出のアサーション。\n",
        'title: "子 SPEC のタイトル"\n'
        'version: "0.1.1"\n'
        "condition: failure\n"
        "labels: []\n"
        'scheduled: ""\n'
        "edges:\n"
        "  # 親 SPEC への辺\n"
        '  - to: "parent-spec"\n'
        '    ref_version: "0.1"\n',
    )
    _node(
        root, "03-analysis/p", "target-p",
        "プロセス P の本文（FND の付与先）。\n",
        'title: "プロセス P"\nversion: "0.2.0"\nlabels: []\nscheduled: ""\nedges: []\n',
    )
    _node(
        root, "04-verification/fnd/open", "fnd-open",
        "**指摘**: P に問題がある。\n\n**深刻度**: low。\n",
        'title: "P の指摘（要確認）"\n'
        'version: "0.1.0"\n'
        "labels: []\n"
        'scheduled: ""\n'
        "edges:\n"
        "  # FND→対象の forward 辺（解決時に逆転）\n"
        '  - to: "target-p"\n'
        '    ref_version: "0.2"\n',
    )
    _node(
        root, "03-analysis/term", "lonely",
        "完全孤立ノード（in/out 辺 0 本）。\n",
        'title: "孤立した用語"\nversion: "0.1.0"\nlabels: []\nscheduled: ""\nedges: []\n',
    )

    _git(root, "init")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "seed")
    return root


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True)
