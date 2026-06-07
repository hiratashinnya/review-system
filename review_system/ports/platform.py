"""System→PF 抽象ポート（LLM 呼び出し）。design/04。

core はこの抽象だけに依存（具体アダプタは adapters/）。MVP は L1 評価のみ。
PF が返す出力も必ずシステムが検証する（triage.validate）＝[10] 不変条件。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..domain.enums import DocumentType
from ..domain.ids import Scope
from ..domain.criteria import CriteriaPack
from ..domain.review import SourceFile, Finding, UnmatchedFinding


@dataclass(frozen=True, slots=True)
class PlatformCapabilities:
    structured_output: bool      # MVP 必須（Q22）
    file_apply: bool
    tool_execution: bool
    model_id: str
    platform_id: str


@dataclass(frozen=True, slots=True)
class ReviewRequest:             # 新規ポート入力型（CLI 境界で文字列→型へ写像済み）
    targets: tuple[SourceFile, ...]
    references: tuple[SourceFile, ...]
    type_override: DocumentType | None
    scope: Scope


@dataclass(frozen=True, slots=True)
class RawReviewResponse:         # PF 出力（=入力・未検証）。検証は core/triage
    findings: tuple[Finding, ...]
    unmatched: tuple[UnmatchedFinding, ...]


class PlatformPort(Protocol):
    def capabilities(self) -> PlatformCapabilities: ...

    def review(
        self,
        pack: CriteriaPack,
        targets: tuple[SourceFile, ...],
        references: tuple[SourceFile, ...],
    ) -> RawReviewResponse: ...
