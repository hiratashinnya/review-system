"""Render the source and item identities supporting the report."""

from .labels import LABELS
from .report_drift import consistency_section, revision_section
from .report_markup import display, html, item_text, repository_slug, timestamp
from .report_observation import checklist_section, collection_scope
from .report_pr_files import pull_files_section

ITEMS = {
    "created": ("起票 Issue", "issues_created", "issues"),
    "closed": ("クローズ Issue", "issues_closed_unknown", "issues"),
    "merged": ("マージ PR（全マージ先）", "pulls_merged", "pull"),
    "issue_transitions": ("クローズ・再オープンのイベント証跡", "issues_close_events", "issues"),
    "issue_transfers": ("期間内の移管イベント証跡", None, "issues"),
    "issues_open_before_cutoff": ("取得対象内で観測上限直前に開いていた Issue（事後復元）",
                                  "issues_open_before_cutoff", "issues"),
    "open_issues": ("オープン Issue", "open_issues", "issues"),
    "open_pulls": ("オープン PR", "open_pulls", "pull"),
}


def _item_suffix(row):
    tags = []
    if row.get("event"):
        kind = {"closed": "クローズ", "reopened": "再オープン", "transferred": "移管"}.get(row["event"], row["event"])
        recorded = row["created_at"]
        effective = row.get("effective_at", recorded)
        tags.append(f"{kind} {timestamp(effective)}")
        if effective != recorded:
            tags.append(f"イベント記録 {timestamp(recorded)}")
    for key in ("state_reason", "base", "reason_source"):
        if row.get(key):
            tags.append(str(row[key]))
    if row.get("draft"):
        tags.append("Draft")
    return " [" + ", ".join(tags) + "]" if tags else ""


def _item_list(label, rows, reason, repository, route):
    items = [f'<li>{item_text(row, repository, route)}{html(_item_suffix(row))}</li>' for row in rows or []]
    contents = f'<ul>{"".join(items)}</ul>' if items else ""
    if reason or rows is None:
        contents = f'<p class="missing">{html(reason or "未取得")}</p>' + contents
    elif not items:
        contents = "<p>0 件</p>"
    return f'<details><summary>{html(label)}</summary>{contents}</details>'


def _source_list(sources):
    rows = []
    for key, source in sources.items():
        count = source.get("retrieved_total")
        result = source.get("reason") or (f"{count} レコード" if count is not None else "件数未取得")
        rows.append(f'<li>{html(key)}　<code>{html(source["source"])}</code>　{html(result)}</li>')
    return "".join(rows)


def evidence_sections(data):
    repository = repository_slug(data["repository"])
    reference = data["reference"]
    base = reference["base_sha"] or reference.get("base_reason") or "未取得"
    limitations = "".join(f'<li>{html(item)}</li>' for item in data["limitations"])
    evidence = {**data["events"], **data["inventory"]}
    sections = []
    for key, (label, metric_key, route) in ITEMS.items():
        if key not in evidence:
            continue
        rows = evidence[key]
        metric = data["metrics"].get(metric_key, {})
        reason = metric.get("reason") if rows is None else None
        if reason:
            reason = display(None, metric.get("status")) + "　" + reason
        sections.append(_item_list(label, evidence.get(f"{key}_known", rows), reason, repository, route))
    sections.extend((checklist_section(data), revision_section(data), pull_files_section(data), consistency_section(data)))
    dirty = "作業ツリーに変更あり" if reference["checkout_dirty"] else "作業ツリー変更なし"
    return f"""
<h2>対象項目と根拠</h2>{"".join(sections)}
<h2>取得元と観測範囲</h2><section>
<p>今回取得の基準 ref <code>{html(reference["base_ref"])}</code> · SHA <code>{html(base)}</code></p>
<p>今回取得の checkout <code>{html(reference["checkout_sha"])}</code>（{dirty}）</p>
{collection_scope(data.get("collection_period"))}
<ul>{_source_list(data["sources"])}{limitations}</ul></section>"""


def chat_summary(data, analysis):
    period = data["period"]
    if data.get("status") == "not_arrived":
        return f'{data["repository"]} {period["start"]} ～ {period["end"]}（未到来）\n'
    partial = "（途中経過）" if period["partial"] else ""
    keys = ("issues_created", "issues_closed_completed", "pulls_merged", "pulls_merged_main", "open_pulls")
    metrics = data["metrics"]
    counts = " / ".join(f'{LABELS[key]} {display(metrics[key]["value"], metrics[key].get("status"))}'
                        for key in keys if key in metrics)
    comparison = data["comparison"]["reason"] or "前回比較あり"
    parts = [f'{data["repository"]} {period["start"]} ～ {period["end"]}{partial}', counts, comparison]
    if analysis:
        parts.append(analysis["summary"].strip())
    return "\n".join(parts) + "\n"
