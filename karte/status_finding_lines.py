from __future__ import annotations



def status_finding_lines(payload: dict) -> list[str]:
    """残存 finding と試行履歴を整形する。"""
    lines: list[str] = []
    lines.append("## 残存 finding（未解消・harm 判定つき）")
    open_lines = [item for item in payload["findings"] if item["status"] == "open"]
    if not open_lines:
        lines.append("  (未解消の指摘なし)")
    for finding in open_lines:
        trace = []
        for attempt in finding["attempts"]:
            outcomes = ", ".join(result["outcome"] for result in attempt["results"]) or "未クローズ"
            trace.append(f"Attempt {attempt['attempt']}({attempt['root_cause']}→{outcomes})")
        disposition = finding["disposition"] or "未決定"
        lines.append(
            f"  - {finding['id']} [harm={finding['harm']}] [scope={finding['scope']}] "
            f"[disposition={disposition}]: {finding['summary']}"
        )
        lines.append(f"      診断/処置: {'; '.join(trace) or '(未診断)'}")
    return lines
