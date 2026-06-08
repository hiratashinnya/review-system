"""P3 評価：観点パック＋対象をガード済み PF へ投げ、生 findings/unmatched を得る。design/02・04。

依存は **SafePlatformPort（ガードプロキシ）**＝例外を投げず StageOutcome を返す（M1）。
ここに try/catch は持たない（門番は adapters.guard が担う）。検証（rule_id・参照除外・
仕分け）は後段（triage）。
"""
from __future__ import annotations

from ..domain.criteria import CriteriaPack
from ..domain.review import NormalizedIntake
from ..domain.result import StageOutcome
from ..ports.platform import SafePlatformPort, RawReviewResponse


def evaluate(
    pack: CriteriaPack, intake: NormalizedIntake, platform: SafePlatformPort
) -> StageOutcome[RawReviewResponse]:
    return platform.review(pack, intake.target_files, intake.reference_files)
