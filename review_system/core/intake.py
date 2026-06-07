"""P1 受付・正規化（use-case）。design/02。

MVP：型は手動上書きのみ（AI 型推定 I-15 は MVP 外）、scope は org 固定。対象/参照集合は
呼び出し側（CLI）が分けて渡す（--ref）。型調停の純粋ロジックは domain.intake に委譲。
"""
from __future__ import annotations

from ..domain.enums import DocumentType
from ..domain.ids import Scope
from ..domain.intake import resolve_document_type  # re-export（純粋ロジック）
from ..domain.review import SourceFile, NormalizedIntake, TypeEstimation

__all__ = ["build_intake", "resolve_document_type"]


def build_intake(
    targets: tuple[SourceFile, ...],
    references: tuple[SourceFile, ...],
    document_type: DocumentType,
    scope: Scope,
) -> NormalizedIntake:
    """確定済みの対象/参照/型/scope から P1 出力（後段の前提）を組む。"""
    return NormalizedIntake(
        target_files=targets,
        reference_files=references,
        document_type=document_type,
        scope=scope,
    )
