"""レポートと版スタンプ（O-1 / S6）。design/01・08。

MVP（P1）の ReviewReport は仕分け4区分＋サマリ＋版スタンプを持つ。🤖 の実適用（ResolvedFix）
は P2（apply・git）で `applied` を足す。stamp.execution_id ＝ review_id（HTML 埋込・DD10）。
"""
from __future__ import annotations

from dataclasses import dataclass

from .ids import ExecutionId, ContentHash
from .review import TriagedFinding, UnmatchedFinding, TriageResult


@dataclass(frozen=True, slots=True)
class ProvenanceStamp:                     # S6 版スタンプ
    execution_id: ExecutionId              # = review_id
    platform_id: str
    model_id: str
    prompt_template_version: str           # 例 "review:3.1"（DD7）
    criteria_content_hash: ContentHash
    executed_at: str                       # ISO8601


@dataclass(frozen=True, slots=True)
class ReportSummary:
    auto_count: int
    approve_count: int
    judge_count: int
    unclassified_count: int

    @classmethod
    def of(cls, result: TriageResult, unclassified: tuple[UnmatchedFinding, ...]) -> "ReportSummary":
        return cls(len(result.auto), len(result.approve), len(result.judge), len(unclassified))


@dataclass(frozen=True, slots=True)
class ReviewReport:                        # O-1（コンテナ・HTML へレンダ）
    auto: tuple[TriagedFinding, ...]       # 🤖（P1 は未適用／P2 で applied 化）
    approve: tuple[TriagedFinding, ...]    # ✋ 要承認
    judge: tuple[TriagedFinding, ...]      # 💬 要判断
    unclassified: tuple[UnmatchedFinding, ...]  # ❓ 未分類
    summary: ReportSummary
    stamp: ProvenanceStamp
