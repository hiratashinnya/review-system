"""Immutable types for feedback document schemas."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    """1つのキーの宣言。

    ``required_nonempty``
        空値（``""``/``[]``/``0``）を認めないか。認めない欄は「必ず書かれる」ことが
        台帳としての価値に直結するもの（誰が・いつ・何を曲げたか）に限る。
    ``lint``
        内容 lint の種別（``owner-verbatim``＝推測語彙の混入拒否＝L4／
        ``inferred``＝``推測：`` マーカー必須＋断定語彙の拒否＝L5）。
    ``ref``
        値が他文書の id を指す欄の種別（実在検査に使う）。
    """

    name: str
    kind: str
    required_nonempty: bool = True
    enum: tuple[str, ...] | None = None
    pattern: re.Pattern | None = None
    lint: str | None = None
    ref: str | None = None
    path_ref: bool = False


@dataclass(frozen=True)
class TableSpec:
    name: str  # "" はトップレベル
    fields: tuple[Field, ...]
    repeated: bool = False
    min_items: int = 0


@dataclass(frozen=True)
class DocSpec:
    kind: str
    schema_const: str
    subdir: str
    id_re: re.Pattern
    tables: tuple[TableSpec, ...]

    def field_map(self) -> dict[str, tuple[TableSpec, Field]]:
        return {
            f"{table.name}.{field.name}" if table.name else field.name: (table, field)
            for table in self.tables
            for field in table.fields
        }
