from __future__ import annotations

from . import model
from .finding_handoff_exemption import is_stall_exempt

STALL_ROUNDS = 3  # 同一 finding の連続未解消ラウンド数


def stalled_ids(karte: model.Karte) -> list:
    """是正対象のうち連続して無進捗の finding ID を返す。"""
    return sorted(
        item.id
        for item in karte.remediation_findings()
        if not is_stall_exempt(item) and item.max_consecutive_rounds() >= STALL_ROUNDS
    )

