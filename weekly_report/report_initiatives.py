"""Display recorded parent–child progress and dependency paths."""

from .report_markup import display, html, item_text, repository_slug


def _at(items, number):
    return items.get(str(number), items.get(number))


def _progress(parent):
    completed, total = parent.get("completed"), parent.get("total")
    value = f'{html(display(completed))} / {html(display(total))} 件完了'
    if type(completed) is int and type(total) is int and 0 <= completed <= total and total > 0:
        value += f'<progress max="{total}" value="{completed}" aria-label="子 Issue の完了件数"></progress>'
    if parent.get("reason"):
        value += f'<br><small class="missing">{html(parent["reason"])}</small>'
    if "known_completed" in parent and completed is None:
        value += f'<br><small>理由を確認できた完了 {html(parent["known_completed"])} 件</small>'
    return f"<p>{value}</p>"


def _membership(change, repository):
    if not change:
        return ""
    if change.get("reason"):
        return f'<p class="missing">分母の比較　{html(change["reason"])}</p>'
    before, current = change.get("previous_total"), change.get("current_total")
    groups = []
    for key, label in (("added", "追加を観測"), ("removed", "除外を観測")):
        if change.get(key):
            items = [item_text(row, repository) if isinstance(row, dict) else html(row) for row in change[key]]
            groups.append(f"<small>{label}　{', '.join(items)}</small>")
    values = f'分母 {html(display(before))} → {html(display(current))} 件'
    return f'<p>{values}<br>{"<br>".join(groups)}</p>'


def _dependencies(rows, blocked_by, repository):
    lines = []
    for row in rows:
        dataset = _at(blocked_by, row["number"])
        if not dataset:
            continue
        source = item_text(row, repository)
        for dependency in dataset.get("rows") or []:
            target = item_text(dependency, repository)
            state = {"open": "オープン", "closed": "クローズ"}.get(dependency.get("state"), "状態不明")
            lines.append(f'<li>{source} <small>→ 前提</small> {target} <small>（{state}）</small></li>')
        if dataset.get("reason"):
            lines.append(f'<li>{source} <small class="missing">{html(dataset["reason"])}</small></li>')
    if not lines:
        return ""
    return f'<p>取得時点の依存経路</p><ul class="dependency-graph">{"".join(lines)}</ul>'


def _children_list(rows, repository):
    if rows is None:
        return '<p class="missing">子 Issue の詳細は未取得です。</p>'
    if not rows:
        return "<p>子 Issue 0 件</p>"
    entries = []
    for row in rows:
        state = "クローズ" if row.get("state") == "closed" else "オープン"
        reason = f' / {html(row["reason"])}' if row.get("reason") else ""
        entries.append(f'<li>{item_text(row, repository)} <small>（{state}{reason}）</small></li>')
    return "<ul>" + "".join(entries) + "</ul>"


def initiatives_section(data):
    inventory = data["inventory"]
    if "initiative_progress" not in inventory:
        return ""
    progress = inventory["initiative_progress"]
    title = "<h2>主要施策の子 Issue</h2>"
    if progress is None:
        return title + '<p class="missing">親子関係 未取得</p>'
    if not progress:
        return title + "<p>取得範囲には表示対象の親 Issue がありません。</p>"
    repository = repository_slug(data["repository"])
    changes = data["comparison"].get("initiative_changes", {})
    blocked_by = inventory.get("blocked_by") or {}
    reports = []
    for parent in progress.values():
        change = _at(changes, parent["number"])
        if parent.get("total") == 0 and not (change or {}).get("removed"):
            continue
        children = parent.get("children")
        dependencies = _dependencies([parent, *(children or [])], blocked_by, repository)
        membership = _membership(change, repository)
        summary = item_text(parent, repository)
        reports.append(f'<details><summary>{summary}</summary>{_progress(parent)}{membership}'
                       f'{_children_list(children, repository)}{dependencies}</details>')
    if not reports:
        return title + "<p>取得範囲には表示対象の親 Issue がありません。</p>"
    return title + "<p>子 Issue の件数に基づく進捗です。機能の利用可否・リリース到達は分析欄を参照します。</p>" + "".join(reports)
