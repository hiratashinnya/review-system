"""Compose the static weekly report from observations and analysis."""

from .analysis import KINDS, OPTIONAL_SECTIONS, SECTIONS
from .comparison import comparison_note
from .report_baseline import baseline_section
from .report_batch import batch_report as batch_report
from .report_cases import derived_cases_section
from .report_evidence import evidence_sections
from .report_initiatives import initiatives_section
from .report_markup import html, link_source, page
from .report_observation import observation_note
from .report_tables import metric_table

_SECTION_LABELS = SECTIONS | OPTIONAL_SECTIONS


def _analysis(analysis, key):
    rows = analysis["sections"].get(key) if analysis is not None else None
    if not rows:
        return ""
    entries = []
    for row in rows:
        sources = " / ".join(link_source(source) for source in row["sources"])
        citation = f'<br><small>根拠　{sources}</small>' if sources else ""
        entries.append(f'<dt>{html(KINDS[row["kind"]])}</dt><dd>{html(row["text"])}{citation}</dd>')
    return f'<section class="analysis"><h2>{html(_SECTION_LABELS[key])}</h2><dl>{"".join(entries)}</dl></section>'


def _sections(data, analysis):
    comparison = data["comparison"]
    parts = [_analysis(analysis, "overview") or "<p>価値評価と着手順の分析は未入力です。</p>"]
    for basis, label in (("period", "期間内の指標と前週差分"), ("observation", "取得時点の残数と実測")):
        note = html(comparison_note(comparison, basis))
        parts.append(f"<h2>{label}</h2><p>{note}</p>{metric_table(data, basis)}")
    parts.extend([
        _analysis(analysis, "delivery"),
        _analysis(analysis, "initiatives"), initiatives_section(data),
        _analysis(analysis, "quality_safety"), derived_cases_section(data, analysis),
        _analysis(analysis, "maintainability"), baseline_section(data),
        _analysis(analysis, "efficiency"), _analysis(analysis, "open_pulls"),
        _analysis(analysis, "next_week"), _analysis(analysis, "owner"), evidence_sections(data),
    ])
    return "\n".join(parts)


def report(data, analysis):
    period = data["period"]
    title = "リポジトリ週次レポート"
    if data.get("status") == "not_arrived":
        return page(title, f'<main><h1>{title}</h1><p>未到来　{html(data.get("reason") or "観測時刻より後の期間です")}</p></main>')
    marker = "途中経過" if period["partial"] else "対象期間終了"
    contents = f'''<header><h1>{title}</h1><p>{html(data["repository"])}</p>
<p class="period">{html(period["start"])} ～ {html(period["end"])}（{marker}）</p>
{observation_note(data)}
<p><a href="snapshot.json">snapshot.json</a> · <a href="summary.txt">チャット用要約</a></p></header>
<main>{_sections(data, analysis)}</main>'''
    return page(title, contents)
