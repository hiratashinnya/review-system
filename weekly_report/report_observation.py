"""Present the dates and coverage of state observations."""

from .report_markup import display, html, item_text, repository_slug

_KINDS = {
    "current": "今回取得した状態",
    "retrospective": "対象期間終了後に取得した状態",
    "saved": "保存済み snapshot の取得時点の状態",
}


def observation_note(data):
    point = data.get("observation")
    if not point:
        return f'<p>観測上限 {html(data["period"]["observed_until"])}　観測時点 {html(data["observed_at"])}</p>'
    when = point.get("observed_at") or data["observed_at"]
    status = point.get("period_end_status")
    details = "期間末の実測あり" if status == "measured" else f'期間末の状態　{display(None, status)}'
    if point.get("period_end_reason"):
        details += f'　{point["period_end_reason"]}'
    saved_sha = point.get("source_snapshot_sha256")
    saved_reference = point.get("reference") or {}
    saved_checkout = saved_reference.get("checkout_sha")
    save_note = f'<br>保存 snapshot の SHA-256 <code>{html(saved_sha)}</code>' if saved_sha else ""
    if saved_checkout:
        platform = html(saved_reference.get("base_ref") or "ref 未取得")
        save_note += f'<br>保存時の checkout <code>{html(saved_checkout)}</code>（{platform}）'
    return (f'<p>イベント集計の上限 {html(data["period"]["observed_until"])}<br>'
            f'イベント証跡の収集 {html(point.get("current_collection_at") or "未取得")}<br>'
            f'{html(_KINDS.get(point.get("kind"), "状態の観測"))} {html(when)}<br>'
            f'<small>{html(details)}{save_note}</small></p>')


def evidence_at_observation(data):
    evidence = data.get("evidence", {})
    if data.get("observation", {}).get("kind") == "saved":
        return evidence.get("saved_observation") or {}, "保存済みの取得時点"
    return evidence, "今回の取得時点"


def collection_scope(period):
    if not period:
        return ""
    dates = f'{html(period["start"])} ～ {html(period["end"])}'
    return f'<p>共通の収集範囲 {dates}　観測上限 {html(period["observed_until"])}</p>'


def _acceptance_row(row, repository):
    title = item_text(row, repository)
    checked = html(display(row.get("checked")))
    total = html(display(row.get("total")))
    evidence = row.get("source_body_sha256") or row.get("source")
    reason = f' <small class="missing">{html(row["reason"])}</small>' if row.get("reason") else ""
    entry = f"<li>{title}　チェック済み {checked} / {total} 件{reason}"
    if evidence:
        entry += f'<br><small>根拠 <code>{html(evidence)}</code></small>'
    return entry + "</li>"


def checklist_section(data):
    inventory = data["inventory"]
    if "issue_acceptance" not in inventory:
        return ""
    rows = inventory["issue_acceptance"]
    if rows is None:
        body = '<p class="missing">未取得</p>'
    else:
        repository = repository_slug(data["repository"])
        entries = [_acceptance_row(row, repository) for row in rows.values()
                   if row.get("total") or row.get("reason")]
        body = f'<ul>{"".join(entries)}</ul>' if entries else "<p>取得範囲内に受け入れ条件のチェック項目はありません。</p>"
    return f'<details><summary>取得時点の受け入れ条件</summary>{body}</details>'
