"""O-1 レポートを**インタラクティブ HTML** に描画（DD10/DD14）。

review_id(=ExecutionId) を埋め込み、finding 毎にチェックボックスで承認/却下/対象外を入力。
「書き出す」ボタン(JS)が <review_id>.feedback.json を download（サーバ無し）。
コマンド側はレポートのパスだけを受け、review_id で同梱 feedback.json を解決する。
"""
from __future__ import annotations

from html import escape

from ..domain.report import ReviewReport
from ..domain.review import TriagedFinding, UnmatchedFinding


def finding_id_str(tf: TriagedFinding) -> str:
    """finding 安定キー（rule_id@file:start-end）。レポートと feedback.json の突合キー。"""
    loc = tf.finding.location
    lr = loc.line_range
    span = f":{lr.start_line}-{lr.end_line}" if lr else ""
    return f"{tf.finding.rule_id.value}@{loc.file}{span}"


def render_html(report: ReviewReport) -> str:
    review_id = report.stamp.execution_id.value
    s = report.summary
    rows = []
    for label, bucket in (("🤖 auto", report.auto), ("✋ approve", report.approve), ("💬 judge", report.judge)):
        for tf in bucket:
            rows.append(_finding_row(label, tf))
    for um in report.unclassified:
        rows.append(_unmatched_row(um))
    body = "\n".join(rows)
    return _TEMPLATE.format(
        review_id=escape(review_id),
        stamp=escape(_stamp_line(report)),
        summary=f"🤖{s.auto_count} ✋{s.approve_count} 💬{s.judge_count} ❓{s.unclassified_count}",
        rows=body,
    )


def _stamp_line(report: ReviewReport) -> str:
    st = report.stamp
    return (f"platform={st.platform_id} model={st.model_id} "
            f"prompt={st.prompt_template_version} criteria={st.criteria_content_hash.value[:12]} "
            f"at={st.executed_at}")


def _finding_row(label: str, tf: TriagedFinding) -> str:
    fid = finding_id_str(tf)
    return (
        f'<tr data-fid="{escape(fid)}" data-kind="triaged">'
        f'<td>{escape(label)}</td>'
        f'<td><code>{escape(fid)}</code></td>'
        f'<td>{escape(tf.finding.rationale)}</td>'
        f'<td><select class="decision">'
        f'<option value="">—</option><option value="approve">承認</option>'
        f'<option value="reject">却下</option><option value="out_of_scope">対象外</option>'
        f'</select></td></tr>'
    )


def _unmatched_row(um: UnmatchedFinding) -> str:
    return (
        f'<tr data-kind="unclassified">'
        f'<td>❓ unclassified</td><td><code>{escape(str(um.location.file))}</code></td>'
        f'<td>{escape(um.description)}</td><td>—</td></tr>'
    )


_TEMPLATE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>Review {review_id}</title>
<style>body{{font-family:sans-serif;margin:1rem}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ccc;padding:4px 8px;text-align:left}}code{{font-size:.85em}}</style>
</head><body data-review-id="{review_id}">
<h1>レビュー結果 <small>{review_id}</small></h1>
<p>{summary}</p><p><small>{stamp}</small></p>
<table><thead><tr><th>区分</th><th>finding</th><th>根拠/説明</th><th>判断</th></tr></thead>
<tbody>
{rows}
</tbody></table>
<button id="export">フィードバックを書き出す</button>
<script>
document.getElementById('export').onclick=function(){{
  var rid=document.body.dataset.reviewId, items=[];
  document.querySelectorAll('tr[data-fid]').forEach(function(tr){{
    var d=tr.querySelector('.decision');
    if(d && d.value) items.push({{finding_id:tr.dataset.fid, decision:d.value}});
  }});
  var blob=new Blob([JSON.stringify({{review_id:rid, feedback:items}}, null, 2)],
                    {{type:'application/json'}});
  var a=document.createElement('a');
  a.href=URL.createObjectURL(blob); a.download=rid+'.feedback.json'; a.click();
}};
</script>
</body></html>
"""
