"""Present sourced case classifications alongside the mechanical proxy."""

from .analysis import CASE_CATEGORIES, KINDS
from .report_markup import html, item_text, link_source, repository_slug


def derived_cases_section(data, analysis):
    metric = data["metrics"].get("defects_per_merge")
    numbers = metric.get("derived_issue_numbers") if metric else None
    if not numbers:
        return ""
    repository = repository_slug(data["repository"])
    items = {row["number"]: row for row in data["events"].get("created") or []}
    annotations = {row["number"]: row for row in (analysis or {}).get("derived_cases", [])}
    lines = []
    for number in numbers:
        issue = items.get(number, {"number": number})
        name = item_text(issue, repository)
        case = annotations.get(number)
        if case:
            category = html(CASE_CATEGORIES[case["category"]])
            kind = html(KINDS[case["kind"]])
            sources = " / ".join(link_source(source) for source in case["sources"])
            details = f'{html(case["text"])}<br><small>根拠　{sources}</small>'
            label = f"{category}（{kind}）"
        else:
            label, details = "不明", "分類の根拠が未入力です。"
        lines.append(f"<tr><th scope=\"row\">{name}</th><td>{label}</td><td>{details}</td></tr>")
    return ("<h2>派生 Issue の事例と根拠</h2>"
            "<p>機械集計の派生事例です。実害欠陥流出の計数は品質指標の一次資料に従います。</p>"
            '<div class="table"><table><thead><tr><th>Issue</th><th>分類</th><th>根拠</th></tr></thead>'
            f'<tbody>{"".join(lines)}</tbody></table></div>')
