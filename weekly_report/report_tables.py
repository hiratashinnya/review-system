"""Metric tables showing values, coverage, measurement definitions and sources."""

from .labels import LABELS
from .report_markup import display, html, link_source


def _breakdown(values):
    return " / ".join(f"{html(name)} {html(value)}" for name, value in values.items())


def _metric_details(metric):
    parts = []
    if metric.get("reason"):
        parts.append(f'<small class="missing">{html(metric["reason"])}</small>')
    if "numerator" in metric or "denominator" in metric:
        pair = (f'分子 {html(display(metric.get("numerator")))} / '
                f'分母 {html(display(metric.get("denominator")))}')
        parts.append(f"<small>{pair}</small>")
    if (count := metric.get("observed_count")) is not None:
        parts.append(f'<small>取得範囲で確かめた件数 {html(count)}</small>')
    if (sample := metric.get("n")) is not None:
        parts.append(f'<small>対象 {html(sample)} 件</small>')
    if metric.get("scope"):
        parts.append(f'<small>{html(metric["scope"])}</small>')
    for status, values in metric.get("observed_by_status", {}).items():
        if values:
            label = {"accepted-debt": "照合済みの既存負債", "violation": "新規・不一致違反"}.get(status, status)
            parts.append(f'<small>{html(label)}　{_breakdown(values)}</small>')
    return "<br>".join(parts)


def _metric_change(delta):
    if not delta:
        return "—"
    if delta.get("reason"):
        return f'— <small>{html(delta["reason"])}</small>'
    result = html(display(delta.get("delta")))
    if "previous" in delta:
        result += f'<br><small>前回 {html(display(delta["previous"]))}</small>'
    return result


def _source(value):
    if isinstance(value, dict):
        return "<br>".join(f"{html(key)}　{_source(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " / ".join(_source(item) for item in value)
    return link_source(value) if value is not None else "出典未取得"


def _metric_row(name, metric, comparison):
    label = LABELS.get(name, name)
    value = display(metric["value"], metric.get("status"))
    unit = f' {metric["unit"]}' if metric["value"] is not None and metric.get("unit") else ""
    detail = _metric_details(metric)
    change = _metric_change(comparison.get(name))
    return (f'<tr><th scope="row">{html(label)}</th><td>{html(value + unit)}<br>{detail}</td>'
            f'<td>{change}</td><td>{html(metric["definition"])}<br>'
            f'<small>{_source(metric["source"])}</small></td></tr>')


def metric_table(data, basis):
    comparison = data["comparison"]["metrics"]
    rows = "".join(_metric_row(name, metric, comparison)
                   for name, metric in data["metrics"].items() if metric["basis"] == basis)
    return (f'<div class="table"><table><thead><tr><th>指標</th><th>値</th><th>前回差</th>'
            f'<th>定義・出典</th></tr></thead><tbody>{rows}</tbody></table></div>')
