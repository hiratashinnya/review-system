"""Render the source and item identities supporting the report."""

from html import escape

from .github import normalize_repository
from .labels import LABELS
from .render import display

ITEMS = {
    "created": ("起票 Issue", "issues_created", "issues"),
    "closed": ("クローズ Issue", "issues_closed_unknown", "issues"),
    "merged": ("マージ PR（全マージ先）", "pulls_merged", "pull"),
    "open_issues": ("オープン Issue", "open_issues", "issues"),
    "open_pulls": ("オープン PR", "open_pulls", "pull"),
}


def _html(value):
    return escape(str(value), quote=True)


def _item_text(row, repository, route):
    number = row["number"]
    label = f'#{_html(number)} {_html(row["title"])}'
    if repository and type(number) is int and number > 0:
        return f'<a href="https://github.com/{repository}/{route}/{number}">{label}</a>'
    return label


def _item_list(label, rows, reason, repository, route):
    items = []
    for row in rows or []:
        tags = []
        if row.get("state_reason"):
            tags.append(row["state_reason"])
        if row.get("draft"):
            tags.append("Draft")
        details = " [" + ", ".join(tags) + "]" if tags else ""
        items.append(f'<li>{_item_text(row, repository, route)}{_html(details)}</li>')
    contents = f'<ul>{"".join(items)}</ul>' if items else ""
    if reason or rows is None:
        contents = f'<p class="missing">{_html(reason or "未取得")}</p>' + contents
    elif not items:
        contents = "<p>0 件</p>"
    return f'<details><summary>{_html(label)}</summary>{contents}</details>'


def evidence_sections(data):
    try:
        repository = normalize_repository(data["repository"])
    except (TypeError, ValueError):
        repository = None
    reference = data["reference"]
    base = reference["base_sha"] or reference["base_reason"]
    sources = "".join(
        f'<li><code>{_html(source["source"])}</code>　'
        f'{_html(source["reason"] or str(source["retrieved_total"]) + " レコード")}</li>'
        for source in data["sources"].values()
    )
    limitations = "".join(f'<li>{_html(item)}</li>' for item in data["limitations"])
    evidence = {**data["events"], **data["inventory"]}
    items = []
    for key, (label, metric, route) in ITEMS.items():
        rows = evidence[key]
        reason = ("未計測　" + data["metrics"][metric]["reason"]) if rows is None and data["metrics"][metric]["reason"] else None
        items.append(_item_list(label, evidence.get(f"{key}_known", rows), reason, repository, route))
    dirty = "作業ツリーに変更あり" if reference["checkout_dirty"] else "作業ツリー変更なし"
    return f"""
<h2>対象項目</h2>{"".join(items)}
<h2>取得元と観測範囲</h2><section>
<p>基準 ref <code>{_html(reference["base_ref"])}</code> · SHA <code>{_html(base)}</code></p>
<p>実測 checkout <code>{_html(reference["checkout_sha"])}</code>（{dirty}）</p>
<ul>{sources}{limitations}</ul></section>"""


def chat_summary(data, analysis):
    partial = "（途中経過）" if data["period"]["partial"] else ""
    keys = ("issues_created", "issues_closed_completed", "pulls_merged", "open_pulls")
    counts = " / ".join(f'{LABELS[key]} {display(data["metrics"][key]["value"])}' for key in keys)
    comparison = data["comparison"]["reason"] or "前回比較あり"
    parts = [f'{data["repository"]} {data["period"]["start"]} ～ {data["period"]["end"]}{partial}', counts,
             comparison]
    if analysis:
        parts.append(analysis["summary"].strip())
    return "\n".join(parts) + "\n"
