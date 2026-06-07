"""P1 受付の純粋ロジック。design/01 §4・[02 P1.1](../../../docs/process/02-decomposition.md)。"""
from __future__ import annotations

from .enums import DocumentType
from .review import TypeEstimation


def resolve_document_type(
    manual_override: DocumentType | None,
    estimation: TypeEstimation | None,
) -> DocumentType | None:
    """文書タイプ調停：I-2 手動上書きを最優先、無ければ I-15 推定。

    両方無ければ None を返し、呼び出し側が S3 fail-close（スコープ未解決の O-14）にする。
    """
    if manual_override is not None:
        return manual_override
    if estimation is not None:
        return estimation.candidate
    return None
