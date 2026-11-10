from __future__ import annotations

from .stall_detection import STALL_ROUNDS
from .status_finding_lines import status_finding_lines


def status_lines(issue, path, payload: dict) -> list[str]:
    """verdict とエスカレーション材料を本文に整形する。"""
    verdict_label = {
        # 申し送り・処置不要の実害ありは台帳に残る。
        "clean": "clean（clean を妨げる未解消の指摘なし）",
        "harmful-open": "harmful-open（clean を妨げる実害ありが残存）",
        "no-harm-only": (
            "no-harm-only（clean を妨げる未解消はすべて実害なし。"
            "申し送り/処置不要と決めた実害ありは別に残りうる）"
        ),
    }[payload["verdict"]]
    lines = [f"=== status: issue-{issue} ==="]
    lines.append(
        f"これは Issue #{issue} の是正ループの進捗判定を、診断カルテ（{path}）から"
        "機械生成した現在状態である（karte status）。"
    )
    lines.append(f"  verdict: {verdict_label}")
    lines.append(f"  未解消: {', '.join(payload['open_findings']) or '(なし)'}")
    # F-495-05: この2行は**台帳上の未解消全件**の harm 別内訳であり、clean を妨げるか否かとは
    # 別の軸（申し送り/処置不要と決めた実害ありもここに出る）。次の行と読み分けられるよう明示する。
    lines.append(
        "  実害あり（未解消・申し送り/処置不要と決めたものを含む）: "
        f"{', '.join(payload['harmful_open']) or '(なし)'}"
    )
    lines.append(f"  実害なし（未解消）: {', '.join(payload['no_harm_open']) or '(なし)'}")
    # Issue #495: 「スコープ外」「別 Issue へ回す」が実害判定・ゲートの免除にならないことを
    # 判定結果の面でも見えるようにする（誰かが気づく必要を残さない）。
    lines.append(
        f"  clean を妨げる未解消: {', '.join(payload['blocking_findings']) or '(なし)'}"
    )
    # 3 集合を包含関係の順に示す。
    lines.append(
        "  clean を妨げる実害あり（verdict harmful-open を成立させている集合）: "
        f"{', '.join(payload['blocking_harmful']) or '(なし)'}"
    )
    lines.append(
        "  実害あり・disposition 未決定（clean を妨げる／scope: out でも免除されない）: "
        f"{', '.join(payload['undecided_disposition']) or '(なし)'}"
    )
    lines.append(
        "  申し送り（disposition: deferred・status は open のまま）: "
        + (
            ", ".join(
                f"{item['id']}→{item['deferred_to']}" for item in payload["deferred_findings"]
            )
            or "(なし)"
        )
    )
    lines.append(
        "  処置不要（disposition: waived・オーナー明示）: "
        + (
            ", ".join(
                f"{item['id']}（{item['waived_by']}）" for item in payload["waived_findings"]
            )
            or "(なし)"
        )
    )
    lines.append(
        f"  スコープ外の申告（scope: out・未解消）: "
        f"{', '.join(payload['out_of_scope_open']) or '(なし)'}"
    )
    lines.append(
        f"  無進捗（{STALL_ROUNDS} ラウンド連続未解消）: "
        f"{', '.join(payload['stalled_findings']) or '(なし)'}"
    )
    if payload.get("handoff_exempt_findings"):
        lines.append("  検証済み申し送り（無進捗から除外）: " + ", ".join(payload["handoff_exempt_findings"]))
    if payload["saturated_groups"]:
        groups = "; ".join(
            "Attempt " + ", ".join(str(number) for number in members)
            for members in payload["saturated_groups"]
        )
        # K-09: 「同種の再試行が拒否される組」であって「次の append が必ず落ちる」ではない。
        lines.append(
            f"  飽和したアプローチ（同種の再試行は append が拒否される）: {groups}"
        )
    if payload["escalate"]:
        reasons = []
        if payload["stalled_findings"]:
            reasons.append(f"無進捗（{', '.join(payload['stalled_findings'])}）")
        if payload["saturated_groups"]:
            reasons.append("飽和したアプローチあり")
        lines.append(f"  escalate: yes（理由: {' / '.join(reasons) or '不明'}）")
    else:
        lines.append("  escalate: no（無進捗・飽和したアプローチのいずれにも該当しない）")
    lines.append("")
    lines.extend(status_finding_lines(payload))
    return lines
