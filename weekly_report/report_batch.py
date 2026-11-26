"""Render an index with the measured periods and comparable weekly trends."""

import re
from datetime import timedelta

from .labels import LABELS
from .period import parse_jst
from .report_markup import display, html, page

_REPORT_PATH = re.compile(r"week-[0-9]{4}-[0-9]{2}-[0-9]{2}/report\.html")
_COLUMNS = ("issues_created", "issues_closed_completed", "pulls_merged_main", "main_baseline_total")


def _complete_week(snapshot, metric):
    period = snapshot["period"]
    if period.get("partial") or metric.get("basis") != "period" or type(metric.get("value")) is not int:
        return False
    start, end = parse_jst(period["start"]), parse_jst(period["end"])
    return end - start == timedelta(days=7) and parse_jst(period["observed_until"]) == end and metric["value"] >= 0


def _signature(metric):
    return metric.get("definition"), metric.get("unit")


def _scales(entries):
    scales = {}
    for key in _COLUMNS[:-1]:
        measured = [metric for snapshot, _ in entries if (metric := snapshot.get("metrics", {}).get(key))
                    and _complete_week(snapshot, metric)]
        if len(measured) >= 2 and all(_signature(metric) == _signature(measured[0]) for metric in measured):
            scales[key] = max(1, max(metric["value"] for metric in measured))
    return scales


def _cell(snapshot, key, scales):
    metric = snapshot.get("metrics", {}).get(key)
    if metric is None:
        return "<td>—</td>"
    value = metric.get("value")
    label = LABELS[key]
    contents = html(display(value, metric.get("status")))
    if key in scales and _complete_week(snapshot, metric):
        contents += f'<meter min="0" max="{scales[key]}" value="{value}" aria-label="{html(label)}"></meter>'
    if metric.get("reason"):
        contents += f'<br><small>{html(metric["reason"])}</small>'
    return f"<td>{contents}</td>"


def _index_row(snapshot, path, scales):
    period = snapshot["period"]
    dates = f'{html(period["start"])} ～ {html(period["end"])}'
    if isinstance(path, str) and _REPORT_PATH.fullmatch(path):
        dates = f'<a href="{html(path)}">{dates}</a>'
    if snapshot.get("status") == "not_arrived":
        status = f'<strong>未到来</strong>　{html(snapshot.get("reason") or "観測の対象時刻に達していません")}'
    else:
        status = "途中経過" if period.get("partial") else "対象期間終了"
    cells = "".join(_cell(snapshot, key, scales) for key in _COLUMNS)
    return f'<tr><th scope="row">{dates}<br><small>{status}</small></th>{cells}</tr>'


def batch_report(entries):
    scales = _scales(entries)
    rows = "".join(_index_row(snapshot, path, scales) for snapshot, path in entries)
    headers = "".join(f'<th scope="col">{html(LABELS[key])}</th>' for key in _COLUMNS)
    contents = ("<header><h1>週次レポート一覧</h1></header><main>"
                '<div class="table"><table><caption>棒は同じ指標定義で完了した7日間の期間集計です。</caption>'
                f'<thead><tr><th scope="col">期間（JST）</th>{headers}</tr></thead>'
                f'<tbody>{rows}</tbody></table></div></main>')
    return page("週次レポート一覧", contents)
