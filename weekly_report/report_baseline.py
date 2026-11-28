"""Explain the recorded baseline at its historical revision."""

from .report_markup import display, html


def _initial_text(initial, metric):
    if initial is None:
        return f'<p class="missing">初期登録 未計測　{html(metric.get("initial_reason") or "根拠未取得")}</p>'
    categories = ("module_lines", "comment_blocks", "mixed_class_files")
    breakdown = " / ".join(f"{html(key)} {html(display(initial.get(key)))}" for key in categories)
    return (f'<p>初期登録 {html(display(initial.get("total")))} 件　{breakdown}<br>'
            f'<small><code>{html(initial.get("commit_sha"))}</code>　{html(initial.get("commit_at"))}</small></p>')


def baseline_section(data):
    metric = data["metrics"].get("main_baseline_total")
    if metric is None:
        return ""
    headline = "<h2>main の保守性 baseline 履歴</h2>"
    note = metric.get("basis_note") or "main の初回登録と対象期間の登録数を比較します。"
    if metric.get("value") is None:
        lines = f'<p class="missing">{html(display(None, metric.get("status")))}　{html(metric.get("reason"))}</p>'
    else:
        lines = (f'<p>対象期間の登録数 {html(metric["value"])} 件<br>'
                 f'基準コミット <code>{html(metric.get("commit_sha"))}</code>　{html(metric.get("commit_at"))}<br>'
                 f'登録ファイルのコミット <code>{html(metric.get("baseline_commit_sha"))}</code></p>')
    initial = _initial_text(metric.get("initial"), metric)
    difference = metric.get("difference_from_initial")
    delta = f'<p>初期登録との差 {html(difference)} 件</p>' if difference is not None else ""
    return f"{headline}<section><p>{html(note)}</p>{lines}{initial}{delta}</section>"
