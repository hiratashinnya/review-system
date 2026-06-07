"""値オブジェクト（識別子・座標・スコープ）。design/01 §1・§3・DD6・DD13。

frozen dataclass なので __eq__/__hash__ は自動生成（値等価＋ハッシュ）。
パスは自前ラッパを作らず pathlib.Path を使う（DD13）。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .enums import InheritanceLayer

if TYPE_CHECKING:                       # 循環 import 回避（FindingId.of の型注釈用）
    from .review import Finding


@dataclass(frozen=True, slots=True)
class RuleId:
    """観点ルールの一意識別子。指摘の紐付け・継承・ポリシー結合キー。"""
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("RuleId は空にできない")


@dataclass(frozen=True, slots=True)
class ContentHash:
    """hash(対象ルールのメタ + 本文)。矛盾キャッシュ(DS2)・警告レジャー(DS4)の照合キー。"""
    value: str


@dataclass(frozen=True, slots=True)
class LineRange:
    """行範囲。(int, int) のタプルを避けて名前付きにする。"""
    start_line: int
    end_line: int

    def __post_init__(self) -> None:
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError("不正な行範囲（start>=1 かつ end>=start）")


@dataclass(frozen=True, slots=True)
class Location:
    """指摘の所在。file は必須（P3 不変条件）、line_range は任意。file は正規化済み Path。"""
    file: Path
    line_range: LineRange | None = None


@dataclass(frozen=True, slots=True)
class Provenance:
    """ルールの由来。衝突報告・差分通知(O-9/Q10)で継承段を示すのに必須。"""
    source_path: Path
    inheritance_layer: InheritanceLayer


@dataclass(frozen=True, slots=True)
class FindingId:
    """revert/コミット粒度（Q3）。rule_id + location から導出する安定キー。"""
    rule_id: RuleId
    location: Location

    @classmethod
    def of(cls, finding: "Finding") -> "FindingId":
        return cls(finding.rule_id, finding.location)


@dataclass(frozen=True, slots=True)
class ExecutionId:
    """1レビュー実行の識別子（=review_id）。版スタンプ(S6)と同素材で再現性に直結（DD6）。"""
    value: str

    @classmethod
    def of(cls, executed_at: str, criteria_hash: ContentHash) -> "ExecutionId":
        return cls(f"{executed_at}-{criteria_hash.value[:12]}")


@dataclass(frozen=True, slots=True)
class Scope:
    """適用スコープ。org は名前なし、team/project は名前付き。"""
    layer: InheritanceLayer
    name: str | None = None

    def __post_init__(self) -> None:
        if self.layer is InheritanceLayer.ORG and self.name is not None:
            raise ValueError("org スコープは名前を持たない")
        if self.layer is not InheritanceLayer.ORG and not self.name:
            raise ValueError("team/project スコープは名前が必須")

    @classmethod
    def org(cls) -> "Scope":               # MVP 既定（意図を名前で表すファクトリ）
        return cls(InheritanceLayer.ORG)
