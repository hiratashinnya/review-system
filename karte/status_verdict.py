from __future__ import annotations

from . import model


def status_verdict(karte: model.Karte):
    """verdict とその根拠となる finding 集合を返す。"""
    open_findings = karte.open_findings()
    harmful = [item for item in open_findings if item.harm == "real"]
    blocking = karte.remediation_findings()
    undecided = karte.undecided_findings()
    blocking_harmful = [item for item in blocking if item.harm == "real"]
    if not blocking:
        verdict = "clean"
    elif blocking_harmful:
        verdict = "harmful-open"
    else:
        verdict = "no-harm-only"
    return open_findings, harmful, blocking, undecided, blocking_harmful, verdict
