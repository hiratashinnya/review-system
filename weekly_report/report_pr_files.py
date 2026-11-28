"""Show PR change paths for dependency and conflict analysis."""

from .report_markup import html, item_text, repository_slug
from .report_observation import evidence_at_observation


def _file(row):
    status = f' <small>{html(row["status"])}</small>' if row.get("status") else ""
    previous = row.get("previous_filename")
    rename = f'<code>{html(previous)}</code> → ' if previous else ""
    return f'<li>{rename}<code>{html(row["filename"])}</code>{status}</li>'


def _paths(pr, evidence, repository):
    name = item_text(pr, repository, "pull")
    if not evidence or evidence.get("rows") is None:
        reason = evidence.get("reason") if evidence else None
        content = f'<p class="missing">{html(reason or "変更ファイルは未取得です。")}</p>'
    elif evidence["rows"]:
        content = f'<ul>{"".join(_file(row) for row in evidence["rows"])}</ul>'
    else:
        content = "<p>変更ファイル 0 件</p>"
    return f'<li>{name}{content}</li>'


def pull_files_section(data):
    evidence, point = evidence_at_observation(data)
    datasets = evidence.get("pull_files")
    if datasets is None:
        return ""
    repository = repository_slug(data["repository"])
    results = []
    for pr in data.get("inventory", {}).get("open_pulls") or []:
        number = pr["number"]
        results.append(_paths(pr, datasets.get(str(number), datasets.get(number)), repository))
    if not results:
        return ""
    return f'<details><summary>オープン PR の変更箇所（{point}）</summary><ul>{"".join(results)}</ul></details>'
