"""① オーケストレーション（P1 通し）。design/06。

段を StageOutcome で直列し、Failure では下流を走らせない（fail-close・S3）。
外部出力（PF）は必ず triage.validate を通る（[10] 不変条件＝PF→直適用の経路は無い）。
MVP は P1（受付→合成→評価→検証・仕分け→レポート）。P2（apply・git・revert）は後続。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..domain.enums import DocumentType
from ..domain.ids import Scope, ExecutionId
from ..domain.criteria import ComposedRule
from ..domain.policy import PolicyMatrix
from ..domain.intake import resolve_document_type
from ..domain.result import StageOutcome, FailureStage, ok, fail
from ..domain.report import ReviewReport, ReportSummary, ProvenanceStamp
from ..ports.platform import PlatformPort, ReviewRequest
from . import compose, evaluate, triage
from .intake import build_intake

# 主たる評価雛形版は registry を単一ソースにする（ハードコード禁止・DRY・DD7）
from ..prompts.registry import REVIEW_VERSION as _PROMPT_TEMPLATE_VERSION


@dataclass(frozen=True, slots=True)
class Deps:
    platform: PlatformPort
    load_criteria: Callable[[DocumentType, Scope], tuple[ComposedRule, ...]]
    load_policy: Callable[[Scope], PolicyMatrix]
    now: Callable[[], str]


def run_review(req: ReviewRequest, deps: Deps) -> StageOutcome[ReviewReport]:
    # P1 受付：型調停（MVP は手動上書きのみ・AI 推定なし）
    doc_type = resolve_document_type(req.type_override, None)
    if doc_type is None:
        return fail(FailureStage.INTAKE, "doc_type が未解決（手動上書きが無い）",
                    None, "--type code|spec|minutes を指定")
    nz = build_intake(req.targets, req.references, doc_type, req.scope)

    # P2 合成（org 最小）
    rules = deps.load_criteria(doc_type, req.scope)
    if not rules:
        return fail(FailureStage.COMPOSE, f"doc_type={doc_type.value} の基準がゼロ（スコープ未解決）",
                    None, "criteria/ に該当 doc_type の観点を用意")
    pack, meta = compose.build_pack_and_meta(rules)

    # P3 評価（PF・アダプタ越し）
    raw = evaluate.evaluate(pack, nz, deps.platform)

    # P4 検証(S1)→参照除外→仕分け(S2)
    valid, unc_from_id = triage.validate(raw.findings, pack)
    unclassified = unc_from_id + raw.unmatched
    reference_paths = {f.path for f in nz.reference_files}
    kept = triage.exclude_reference(valid, reference_paths)
    result = triage.triage(kept, meta, deps.load_policy(req.scope))

    # P5 レポート組立＋S6 版スタンプ
    criteria_hash = compose.content_hash(rules)
    caps = deps.platform.capabilities()
    executed_at = deps.now()
    stamp = ProvenanceStamp(
        execution_id=ExecutionId.of(executed_at, criteria_hash),
        platform_id=caps.platform_id,
        model_id=caps.model_id,
        prompt_template_version=_PROMPT_TEMPLATE_VERSION,
        criteria_content_hash=criteria_hash,
        executed_at=executed_at,
    )
    report = ReviewReport(
        auto=result.auto,
        approve=result.approve,
        judge=result.judge,
        unclassified=unclassified,
        summary=ReportSummary.of(result, unclassified),
        stamp=stamp,
    )
    return ok(report)
