"""Read existing local evidence once and project report metrics from it."""

from . import ledger_advisory, ledger_feedback, ledger_karte, local
from .quantities import measured


def capture(root):
    return {"maintainability": local.capture_maintainability(root), "owner_proposals": ledger_feedback.capture(root),
            "advisory": ledger_advisory.capture(root), "karte": ledger_karte.capture(root)}


def observation_metrics(evidence, *, observed_at=None):
    return {"maintainability_violations": local.measure_maintainability(evidence["maintainability"]),
            **ledger_feedback.measure(evidence["owner_proposals"], observed_at),
            **ledger_karte.measure(evidence["karte"])}


def period_metrics(period, evidence):
    return {
        **ledger_advisory.measure(period, evidence["advisory"]),
        "owner_decision_wait_days": ledger_feedback.measure_decisions(period, evidence["owner_proposals"]),
        "post_merge_harmful_defects": measured(
            None, "期間内に初めて判明したマージ後の実害欠陥",
            ["#370", "#827", "audit/2026-11-03-pr-issue-mistake-patterns/DESIGN-L4-L6.md"],
            reason="期間・対象を網羅する確定分類の一次証跡がありません。派生 Issue 数は別の指標です。",
            numerator=None, denominator=None,
        ),
    }
