from __future__ import annotations

from . import model
from .stall_detection import stalled_ids


def render_finding_lines(karte: model.Karte) -> list[str]:
    """未解消 finding を整形する。"""
    lines: list[str] = []
    lines.append("## Open findings（未解消）")
    open_findings = karte.open_findings()
    if not open_findings:
        lines.append("  (未解消の指摘なし)")
    stalled_finding_ids = set(stalled_ids(karte))
    for finding in open_findings:
        # 無進捗の印は stall_detection.stalled_ids から引く。
        # この判定は finding_handoff_exemption.is_stall_exempt を追加で除く。
        stalled = " ★無進捗" if finding.id in stalled_finding_ids else ""
        lines.append(
            f"  - {finding.id} [harm={finding.harm}] [severity={finding.severity}] "
            f"[scope={finding.scope}] [disposition={finding.disposition or '未決定'}]"
            f" rounds={finding.rounds}{stalled}"
        )
        # Issue #495: 是正側にも「スコープ外の申告は処置免除ではない」ことを本文で示す
        # （`scope: out` を理由に直さず素通しする、が塞ごうとしている経路そのもの）。
        if finding.scope == "out":
            lines.append(
                "      注意: scope: out（スコープ外の申告）は実害判定・記録・verdict の"
                "免除にならない。処置方針（disposition）は主文脈／オーナーが決める。"
            )
        if finding.disposition == "deferred":
            lines.append(f"      申し送り先: {finding.deferred_to}（この PR では直さない）")
        if finding.disposition == "waived":
            lines.append(
                f"      処置不要（waived）: {finding.waived_by} / {finding.waived_reason}"
            )
        lines.append(f"      summary: {finding.summary}")
        lines.append(f"      harm_detail: {finding.harm_detail}")
        if finding.locus:
            lines.append(f"      locus: {', '.join(finding.locus)}")
        lines.append(f"      evidence: {finding.evidence}")
        # expected / recheck は是正側の入力契約そのもの（Issue #341 F-341-01）。
        # ここに出さないと `issue-fixer` は「何をもって解消か」を前ラウンドから引けない。
        lines.append(f"      expected: {finding.expected}")
        lines.append(f"      recheck: {finding.recheck}")
        related = karte.attempts_for_finding(finding.id)
        if related:
            lines.append(
                "      対応した Attempt: "
                + ", ".join(str(item.number) for item in related)
            )

    return lines
