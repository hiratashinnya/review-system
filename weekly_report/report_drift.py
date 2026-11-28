"""Display detected GitHub collection changes and revision-bound PR evidence."""

from .report_markup import html, item_text, repository_slug
from .report_observation import evidence_at_observation

_CHANGE = {"added": "追加", "missing": "取得後の一覧に不在", "updated": "更新"}
_STATUS = {"unknown": "未確認", "changed": "変化あり", "unchanged": "比較対象の項目は一致"}


def _change(change):
    fields = "・".join(html(field) for field in change.get("fields", []))
    label = html(_CHANGE.get(change.get("kind"), change.get("kind")))
    details = f'（{fields}）' if fields else ""
    if "before_head_sha" in change:
        old = html(change["before_head_sha"] or "未取得")
        new = html(change.get("after_head_sha") or "未取得")
        details += f'　HEAD <code>{old}</code> → <code>{new}</code>'
    return f'<li>#{html(change["number"])}　{label}{details}</li>'


def consistency_section(data):
    recorded = data.get("evidence", {}).get("consistency")
    if not recorded:
        return ""
    labels = {"issues": "Issue", "pulls": "PR"}
    lines = []
    for key, result in recorded.items():
        status = _STATUS.get(result.get("status"), result.get("status"))
        fields = [status, result.get("reason"), result.get("source")]
        description = "　".join(html(item) for item in fields if item)
        changes = "".join(_change(change) for change in result.get("changed") or [])
        proof = f'<ul>{changes}</ul>' if changes else ""
        lines.append(f'<li>{html(labels.get(key, key))}　{description}{proof}</li>')
    return f'<details><summary>今回の取得中の整合性</summary><ul>{"".join(lines)}</ul></details>'


def _recorded_ids(values, dataset, reason):
    if values is None or (not values and reason):
        return "未確認"
    if not values:
        return "取得範囲内の一致 0 件"
    rows = {row["id"]: row for row in (dataset or {}).get("rows") or []}
    parts = []
    for value in values:
        row = rows.get(value) or {}
        state = row.get("conclusion") or row.get("status") or row.get("state")
        parts.append(f'{html(value)}（{html(state)}）' if state else html(value))
    return ", ".join(parts)


def _pr_row(number, row, identity, evidence, repository):
    name = item_text(identity, repository, "pull")
    sha = row.get("head_sha")
    if not sha:
        sha = "未確認"
    workflow_reason, review_reason = row.get("workflow_reason"), row.get("review_reason")
    workflows = (evidence.get("head_ci") or {}).get(sha)
    results = evidence.get("reviews") or {}
    reviews = results.get(number, results.get(str(number)))
    jobs = _recorded_ids(row.get("matching_workflow_run_ids"), workflows, workflow_reason)
    posts = _recorded_ids(row.get("matching_review_ids"), reviews, review_reason)
    scope = html(row.get("workflow_scope") or "SHA 一致の候補")
    reasons = "".join(f'<br>{label}　{html(reason)}' for label, reason in (("CI", workflow_reason), ("レビュー", review_reason)) if reason)
    return (f'<li>{name}　HEAD <code>{html(sha)}</code><br><small>CI（{scope}） {jobs} ／同一 SHA のレビュー {posts}'
            f'{reasons}</small></li>')


def revision_section(data):
    evidence, point = evidence_at_observation(data)
    if "pull_heads" not in evidence:
        return ""
    heads = evidence["pull_heads"]
    if heads is None:
        body = '<p class="missing">PR の対象 HEAD 未取得</p>'
    elif not heads:
        body = "<p>取得範囲に照合対象の PR はありません。</p>"
    else:
        repository = repository_slug(data["repository"])
        pulls = (data.get("inventory", {}).get("open_pulls") or []) + (data.get("events", {}).get("merged") or [])
        identities = {str(row["number"]): row for row in pulls}
        lines = [_pr_row(number, row, identities.get(str(number), {"number": number, "title": row.get("title")}),
                         evidence, repository) for number, row in heads.items()]
        body = f'<ul>{"".join(lines)}</ul>'
    return f'<details><summary>PR の HEAD と照合した証跡（{point}）</summary>{body}</details>'
