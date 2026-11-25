"""Render static HTML, escaping all non-template values."""

from html import escape

from .analysis import KINDS, SECTIONS
from .comparison import comparison_note
from .labels import LABELS
from .snapshot import dumps

STYLE = """
:root{font-family:system-ui,sans-serif;color:#192935;background:#f5f7fa}
body{margin:0 auto;padding:1.5rem;max-width:74rem}
h1{font-size:clamp(1.8rem,4vw,2.8rem);margin:.25em 0}
h2{margin-top:1.7em} h3{margin-top:1.3em}
a{color:#07558e} code{overflow-wrap:anywhere}
section,details{background:white;border:1px solid #d6e0e8;border-radius:.55rem;padding:1rem;margin:.7rem 0}
table{width:100%;border-collapse:collapse}
td,th{text-align:left;vertical-align:top;border-bottom:1px solid #d6e0e8;padding:.5rem}
small{color:#414e5b} .missing{color:#8b361f}
.analysis dt{font-weight:700} .analysis dd{white-space:pre-wrap;margin:0 0 .9em}
.table{overflow-x:auto} .period{font-weight:650}
"""


def _html(value):
    return escape(str(value), quote=True)


def display(value):
    if value is None:
        return "未計測"
    return f"{value:.2f}" if type(value) is float else str(value)


def _analysis(value):
    if value is None:
        return "<p>定量集計を表示しています。価値評価と着手順の分析は未入力です。</p>"
    parts = []
    for key, label in SECTIONS.items():
        parts.append(f'<section class="analysis"><h3>{_html(label)}</h3><dl>')
        for row in value["sections"][key]:
            sources = " / ".join(row["sources"])
            citation = f'<br><small>根拠　{_html(sources)}</small>' if sources else ""
            parts.append(f'<dt>{_html(KINDS[row["kind"]])}</dt><dd>{_html(row["text"])}{citation}</dd>')
        parts.append("</dl></section>")
    return "\n".join(parts)


def _metric_row(name, metric, comparison):
    label = LABELS.get(name, name)
    value = display(metric["value"])
    unit = " " + metric["unit"] if metric["value"] is not None and metric.get("unit") else ""
    detail = f'<small class="missing">{_html(metric["reason"])}</small>' if metric["reason"] else ""
    if "numerator" in metric:
        detail += f' <small>分子 {_html(metric["numerator"])} / 分母 {_html(metric["denominator"])}</small>'
    if "observed_by_status" in metric:
        debt = metric["observed_by_status"]
        detail += f'<br><small>実測内訳 {_html(dumps(debt).replace(chr(10), " "))}</small>'
    delta = comparison.get(name)
    change = "—" if delta is None else _html(display(delta["delta"]))
    if delta and delta["reason"]:
        change = f'— <small>{_html(delta["reason"])}</small>'
    elif delta and "previous" in delta:
        change += f'<br><small>前回 {_html(display(delta["previous"]))}</small>'
    return (f'<tr><th scope="row">{_html(label)}</th><td>{_html(value + unit)}<br>{detail}</td>'
            f'<td>{change}</td><td>{_html(metric["definition"])}<br>'
            f'<small>{_html(metric["source"])}</small></td></tr>')


def _table(data, basis):
    rows = "".join(_metric_row(name, metric, data["comparison"]["metrics"])
                   for name, metric in data["metrics"].items() if metric["basis"] == basis)
    return (f'<div class="table"><table><thead><tr><th>指標</th><th>値</th><th>前回差</th>'
            f'<th>定義・出典</th></tr></thead><tbody>{rows}</tbody></table></div>')


def report(data, analysis):
    from .report_evidence import evidence_sections

    period = data["period"]
    marker = "途中経過" if period["partial"] else "対象期間終了"
    comparison = data["comparison"]
    return f'''<!doctype html>
<html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>リポジトリ週次レポート</title><style>{STYLE}</style>
<body><header><h1>リポジトリ週次レポート</h1><p>{_html(data["repository"])}</p>
<p class="period">{_html(period["start"])} ～ {_html(period["end"])}（{marker}）</p>
<p>観測上限 {_html(period["observed_until"])}　観測時点 {_html(data["observed_at"])}</p>
<p><a href="snapshot.json">snapshot.json</a> · <a href="summary.txt">チャット用要約</a></p></header>
<main><h2>今週の評価と次週の計画</h2>{_analysis(analysis)}
<h2>期間内の指標</h2><p>{_html(comparison_note(comparison, "period"))}</p>{_table(data, "period")}
<h2>観測時の残数と実測</h2><p>{_html(comparison_note(comparison, "observation"))}</p>{_table(data, "observation")}
{evidence_sections(data)}
</main></body></html>'''
