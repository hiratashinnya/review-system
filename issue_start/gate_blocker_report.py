from __future__ import annotations

from typing import Any, Mapping

from .gate_support import IssueStartError



def _blocker_report(collector: Any, blocker: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not hasattr(collector, "issue_metadata"):
        raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
    report: list[dict[str, Any]] = []
    seen: set[str] = set()
    for finding in blocker.get("findings", []):
        if finding.get("code") != "OPEN_BLOCKER" or finding.get("waiver_id") is not None:
            continue
        path = finding.get("path")
        if not isinstance(path, list) or not path or not isinstance(path[-1], str):
            raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
        blocker_ref = path[-1]
        if "#" not in blocker_ref:
            raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
        repository, raw_number = blocker_ref.rsplit("#", 1)
        if not raw_number.isdigit():
            raise IssueStartError("ISSUE_START_REPORT_CONTRACT_ERROR")
        if blocker_ref in seen:
            continue
        seen.add(blocker_ref)
        try:
            metadata = collector.issue_metadata(repository, int(raw_number))
        except IssueStartError:
            raise
        except Exception as exc:
            raise IssueStartError("ISSUE_START_REPORT_API_ERROR", type(exc).__name__) from exc
        title = metadata.get("title")
        url = metadata.get("html_url")
        if not isinstance(title, str) or not title or not isinstance(url, str) or not url:
            raise IssueStartError("ISSUE_START_REPORT_API_PARTIAL")
        report.append({
            "number": int(raw_number),
            "repository": repository,
            "title": title,
            "url": url,
            "path": path,
            "next_action": "blockerをcloseするかblocking relationを解消し、fresh invocationで再試行する",
        })
    return report
