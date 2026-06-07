"""P3 評価：観点パック＋対象を PF へ投げ、生 findings/unmatched を得る。design/02。

ここでは PF（アダプタ）を呼ぶだけ。出力の検証（rule_id・参照除外・仕分け）は後段（triage）。
"""
from __future__ import annotations

from ..domain.criteria import CriteriaPack
from ..domain.review import NormalizedIntake
from ..ports.platform import PlatformPort, RawReviewResponse


def evaluate(pack: CriteriaPack, intake: NormalizedIntake, platform: PlatformPort) -> RawReviewResponse:
    return platform.review(pack, intake.target_files, intake.reference_files)
