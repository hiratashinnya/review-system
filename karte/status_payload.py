from __future__ import annotations

from . import model
from .finding_handoff_exemption import is_stall_exempt
from .saturation_groups import saturated_groups
from .stall_detection import STALL_ROUNDS, stalled_ids
from .status_findings import finding_rows
from .status_verdict import status_verdict


def status_payload(karte: model.Karte) -> dict:
    """verdict とエスカレーション材料を集計する。"""
    open_findings, harmful, blocking, undecided, blocking_harmful, verdict = status_verdict(karte)
    findings = finding_rows(karte)
    stalled = stalled_ids(karte)
    # K-09: 表示（ここ）とゲート（append）は同じ判定関数を使う。`saturated_groups` は
    # 「そのアプローチを繰り返す append が拒否される」既存 Attempt の組。
    saturated = [members for _number, members, _hits, _candidate in saturated_groups(karte)]
    payload = {
        "issue": karte.issue,
        "verdict": verdict,
        "open_findings": [item.id for item in open_findings],
        "harmful_open": [item.id for item in harmful],
        "no_harm_open": [item.id for item in open_findings if item.harm == "none"],
        # Issue #495: verdict のゲート材料。`blocking_findings` が空のときだけ clean。
        "blocking_findings": [item.id for item in blocking],
        # PR #496 F-495-06: `blocking_findings` ∩ `harmful_open`＝「clean を妨げる実害あり」。
        # verdict `harmful-open` を成立させている当の集合なので、消費者に積を取らせず出す。
        "blocking_harmful": [item.id for item in blocking_harmful],
        "undecided_disposition": [item.id for item in undecided],
        "deferred_findings": [
            {"id": item.id, "deferred_to": item.deferred_to}
            for item in open_findings
            if item.disposition == "deferred"
        ],
        "waived_findings": [
            {"id": item.id, "waived_by": item.waived_by, "waived_reason": item.waived_reason}
            for item in open_findings
            if item.disposition == "waived"
        ],
        "out_of_scope_open": [item.id for item in open_findings if item.scope == "out"],
        "stalled_findings": stalled,
        "stall_rounds": STALL_ROUNDS,
        "saturated_groups": saturated,
        "escalate": bool(stalled or saturated),
        "findings": findings,
    }
    exempt = [item.id for item in karte.remediation_findings() if is_stall_exempt(item)]
    if exempt:
        payload["handoff_exempt_findings"] = exempt
    return payload
