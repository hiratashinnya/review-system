"""Issue #614: check 固有の診断免除。verdict の blocking 集合は変更しない。"""

from .finding_handoff_exemption import is_stall_exempt


def exemption_reason(finding, pending_overrides: dict) -> str | None:
    """理由を返す。None は診断必須（安全側）。"""
    if not finding.is_open:
        return None
    if finding.cleared_by_disposition:
        return finding.disposition
    if finding.disposition == "fix-here" and finding.diagnosis_owner == "main":
        return "主文脈担当（fix-here は未解消のまま）"
    if finding.harm != "none":
        return None
    if finding.disposition == "deferred" and is_stall_exempt(finding):
        return "検証済み handoff（harm: none / deferred）"
    if finding.disposition == "waived" and finding.id not in pending_overrides:
        return "検証済み owner override（harm: none / waived）"
    return None
