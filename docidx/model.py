"""docidx のドメインモデル（不変データ型）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Edge:
    """無名依存辺（``to`` への依存・``ref_version`` は参照先バッジ x.y）。

    依存仕様: 04-notation.md §3（`to` スカラ・`ref_version` 必須・`note` 任意・`kind`/`status` なし）。
    """

    to: str
    ref_version: str = ""
    note: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Edge":
        return cls(
            to=str(d.get("to", "")),
            ref_version=str(d.get("ref_version", "")),
            note=str(d.get("note", "")),
        )


@dataclass(frozen=True)
class Node:
    """doc-system の 1 ノード（summary バッジ＋YAML＋本文）。

    依存仕様: SPEC-1-1 v0.1（構造化フィールド）。``version`` は summary バッジ x.y が
      真実源＝02-meta-schema.md §1（DD-8・ファイル frontmatter version は廃止）。
    """

    id: str
    type: str
    version: str  # summary バッジの x.y
    heading: str
    file: str  # リポジトリ root からの相対パス（posix）
    line: int  # summary 行の 1 始まり行番号
    labels: tuple[str, ...] = ()
    scheduled: str = ""
    condition: str = ""
    edges: tuple[Edge, ...] = ()
    body: str = ""
    fields: dict[str, Any] = field(default_factory=dict)  # 上記以外の YAML スカラ
    parse_error: str | None = None  # YAML がパースできなかった場合の理由

    def summary_row(self) -> dict[str, Any]:
        """インデックス/検索用の軽量行（本文を含まない）。"""
        row: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "version": self.version,
            "heading": self.heading,
            "labels": list(self.labels),
            "scheduled": self.scheduled,
            "file": self.file,
            "line": self.line,
            "edge_count": len(self.edges),
        }
        if self.condition:
            row["condition"] = self.condition
        if self.parse_error:
            row["parse_error"] = self.parse_error
        return row

    def to_dict(self) -> dict[str, Any]:
        """``show`` 用のノード全体表現。"""
        d = self.summary_row()
        d.pop("edge_count", None)
        d["edges"] = [
            {"to": e.to, "ref_version": e.ref_version, **({"note": e.note} if e.note else {})}
            for e in self.edges
        ]
        if self.fields:
            d["fields"] = self.fields
        d["body"] = self.body
        return d


@dataclass(frozen=True)
class NodeIndex:
    """全ノードと、ID 索引・依存元（逆引き）索引。"""

    nodes: tuple[Node, ...]
    by_id: dict[str, Node]
    dependents: dict[str, tuple[str, ...]]  # target_id -> それを参照する node id 群

    @classmethod
    def build(cls, nodes: list[Node]) -> "NodeIndex":
        by_id: dict[str, Node] = {}
        rev: dict[str, list[str]] = {}
        for n in nodes:
            by_id.setdefault(n.id, n)  # 先勝ち（重複 ID は最初を保持）
            for e in n.edges:
                rev.setdefault(e.to, []).append(n.id)
        dependents = {k: tuple(v) for k, v in rev.items()}
        return cls(nodes=tuple(nodes), by_id=by_id, dependents=dependents)
