"""Shared markup for a static weekly report and its batch index."""

from datetime import datetime
from html import escape
import re

from .github import REPOSITORY, normalize_repository

_REPO_PATH = REPOSITORY.pattern
_GITHUB_ITEM_URL = re.compile(
    rf"https://github\.com/{_REPO_PATH}/(?:issues|pull)/[1-9][0-9]*"
    r"(?:#(?:issuecomment-|discussion_r|pullrequestreview-)[0-9]+)?"
)
_REPOSITORY_URL = re.compile(rf"https://api\.github\.com/repos/({_REPO_PATH})")

STYLE = """
:root{font-family:system-ui,sans-serif;color:#192935;background:#f5f7fa;line-height:1.55}
body{margin:0 auto;padding:1.5rem;max-width:74rem}
h1{font-size:clamp(1.8rem,4vw,2.8rem);margin:.25em 0}
h2{margin-top:1.7rem} h3{margin-top:1.3rem}
a{color:#07558e} code{overflow-wrap:anywhere}
section,details{background:white;border:1px solid #d6e0e8;border-radius:.55rem;padding:1rem;margin:.7rem 0}
summary{cursor:pointer;font-weight:650}
table{width:100%;border-collapse:collapse}
td,th{text-align:left;vertical-align:top;border-bottom:1px solid #d6e0e8;padding:.5rem}
small{color:#414e5b} .missing{color:#8b361f}
.analysis dt{font-weight:700} .analysis dd{white-space:pre-wrap;margin:0 0 .9rem}
.table{overflow-x:auto} .period{font-weight:650}
meter,progress{display:block;width:100%;max-width:12rem;accent-color:#07558e}
.dependency-graph li{margin:.45rem 0}
"""

STATES = {
    "not_retrieved": "未取得",
    "not_measured": "未計測",
    "not_calculable": "算出不能",
}


def html(value):
    return escape(str(value), quote=True)


def display(value, status=None):
    if value is None:
        return STATES.get(status, "未計測") if isinstance(status, str) else "未計測"
    return f"{value:.2f}" if type(value) is float else str(value)


def link_source(value):
    label = html(value)
    if isinstance(value, str) and _GITHUB_ITEM_URL.fullmatch(value):
        return f'<a href="{label}">{label}</a>'
    return label


def timestamp(value):
    return value.isoformat() if isinstance(value, datetime) else value


def repository_slug(value):
    try:
        return normalize_repository(value)
    except (ValueError, TypeError):
        return None


def item_repository(row, fallback=None):
    if "repository_url" not in row:
        return fallback
    source = row["repository_url"]
    match = _REPOSITORY_URL.fullmatch(source) if isinstance(source, str) else None
    return repository_slug(match[1]) if match else None


def item_text(row, repository, route="issues"):
    number = row.get("number")
    label = f'#{html(number)} {html(row.get("title") or "タイトル未取得")}'
    repository = item_repository(row, repository)
    if repository and route in ("issues", "pull") and type(number) is int and number > 0:
        return f'<a href="https://github.com/{repository}/{route}/{number}">{label}</a>'
    return label


def page(title, contents):
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>{html(title)}</title><style>{STYLE}</style></head>
<body>{contents}</body></html>'''
