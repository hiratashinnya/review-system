"""レビュー導出物（P1 受付・P3 評価の値）。design/01 §4。すべて frozen。"""
from __future__ import annotations

from dataclasses import dataclass

from .enums import DocumentType, ApplicationMode, TriageBucket
from .ids import Location, RuleId, Scope
from pathlib import Path

_MODE_TO_BUCKET = {
    ApplicationMode.AUTO_FIX_LOG_ONLY: TriageBucket.AUTO,
    ApplicationMode.AUTO_FIX_SUGGEST: TriageBucket.APPROVE,
    ApplicationMode.HUMAN_ONLY: TriageBucket.JUDGE,
}


@dataclass(frozen=True, slots=True)
class SourceFile:
    path: Path                              # 正規化済み pathlib.Path（DD13）
    content: str
    language: str | None = None


@dataclass(frozen=True, slots=True)
class TypeEstimation:                        # PF 出力（=入力・L3/I-15）
    candidate: DocumentType
    confidence: float


@dataclass(frozen=True, slots=True)
class NormalizedIntake:                      # P1 の出力＝後段すべての前提
    target_files: tuple[SourceFile, ...]    # 対象集合（評価する物）
    reference_files: tuple[SourceFile, ...] # 参照集合（評価しない物）
    document_type: DocumentType             # 調停済み確定型
    scope: Scope


@dataclass(frozen=True, slots=True)
class SuggestedFix:
    description: str
    diff: str


@dataclass(frozen=True, slots=True)
class Finding:                              # PF 生成（=入力）→ 検証後に O-2
    rule_id: RuleId
    location: Location                     # file 必須は Location が保証
    rationale: str
    quote: str | None = None
    suggested_fix: SuggestedFix | None = None


@dataclass(frozen=True, slots=True)
class UnmatchedFinding:                     # O-7 ❓未分類
    description: str
    location: Location
    suggested_fix: SuggestedFix | None = None


@dataclass(frozen=True, slots=True)
class TriagedFinding:                       # P4.3 出力：finding＋適用モード
    finding: Finding
    mode: ApplicationMode

    @property
    def bucket(self) -> TriageBucket:       # mode から決定的に導出（状態を持たない）
        return _MODE_TO_BUCKET[self.mode]


@dataclass(frozen=True, slots=True)
class TriageResult:                         # 4区分の束
    auto: tuple[TriagedFinding, ...]
    approve: tuple[TriagedFinding, ...]
    judge: tuple[TriagedFinding, ...]
    unclassified: tuple[UnmatchedFinding, ...]
