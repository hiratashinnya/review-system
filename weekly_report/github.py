"""Read GitHub REST pages with gh, preserving failure and coverage evidence."""

import json
import re
import subprocess

REPOSITORY = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*")


def normalize_repository(repository):
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("--repository は OWNER/REPO 形式で指定してください")
    return repository.lower()


def evidence(source, rows=None, *, reason=None, **coverage):
    return {"source": source, "rows": rows, "reason": reason, **coverage}


def decode_pages(output):
    decoder = json.JSONDecoder()
    pages = []
    rest = output.lstrip()
    more = True
    while rest:
        headers, boundary, document = rest.partition("\n\n")
        if not more or not boundary or not re.match(r"HTTP/\S+ 200(?: |\n)", headers):
            raise ValueError("API ページヘッダーが不正です")
        page, end = decoder.raw_decode(document)
        pages.append(page)
        link = re.search(r"(?im)^Link: (.*)$", headers)
        more = link is not None and 'rel="next"' in link[1]
        rest = document[end:].lstrip()
    if not pages or more:
        raise ValueError("API ページが不足しています")
    return pages


def _page_rows(pages, collection):
    if not collection:
        return pages, None
    counts = {page["total_count"] for page in pages}
    count = counts.pop()
    if counts or type(count) is not int or count < 0:
        raise ValueError("ページ間で total_count が一致しません")
    return [page[collection] for page in pages], count


def get(repository, endpoint, max_pages, *, convert, collection=None):
    path = f"repos/{repository}/{endpoint}"
    source = "https://api.github.com/" + path
    try:
        response = subprocess.run(
            ["gh", "api", "--hostname", "github.com", "--method", "GET", "--paginate", "--include", path],
            capture_output=True, text=True, check=False, timeout=120,
        )
        if response.returncode:
            error = re.search(r"HTTP (\d{3})", response.stderr)
            detail = f"HTTP {error[1]}" if error else f"gh exit {response.returncode}"
            return evidence(source, reason=f"GitHub API の取得失敗 ({detail})")
        return _complete_rows(source, decode_pages(response.stdout), max_pages, collection, convert)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return evidence(source, reason=f"GitHub API の実行失敗 ({type(exc).__name__})")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        return evidence(source, reason=f"GitHub API の応答不正 ({type(exc).__name__})")


def _complete_rows(source, pages, max_pages, collection, convert):
    if len(pages) >= max_pages:
        return evidence(source, reason="ページ上限に到達し、完全性を確認できません", pages=len(pages))
    batches, count = _page_rows(pages, collection)
    if any(not isinstance(batch, list) for batch in batches):
        raise ValueError("ページが配列ではありません")
    rows = [convert(row) for batch in batches for row in batch]
    keys = {row.get("id", row.get("number")) for row in rows}
    if len(keys) != len(rows):
        return evidence(source, reason="ページ間に重複があり、完全性を確認できません", pages=len(pages))
    if count is not None and (count >= 1000 or count != len(rows)):
        return evidence(source, reason="API の検索上限、または total_count と取得件数の不一致", pages=len(pages),
                        reported_total=count, retrieved_total=len(rows))
    return evidence(source, rows, pages=len(pages), retrieved_total=len(rows))
