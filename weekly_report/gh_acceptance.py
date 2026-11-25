"""Preserve observable Issue acceptance criteria checkbox evidence."""

import hashlib
import re

HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)(?:[ \t]+#+)?[ \t]*$")
AC_TITLE = re.compile(r"^(?:acceptance\s+criteria\b|受け入れ条件|受入条件|AC\b)", re.IGNORECASE)
CHECKBOX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[([ xX])\]\s+(\S.*)$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def acceptance_evidence(issue):
    body = issue.get("body")
    number = issue["number"]
    items = _checkboxes(body) if body else []
    return {
        "number": number, "title": issue["title"], "source": f"GitHub REST issues/{number} body",
        "source_body_sha256": hashlib.sha256(body.encode()).hexdigest() if body is not None else None,
        "items": items if items else None,
        "checked": sum(item["checked"] for item in items) if items else None,
        "total": len(items) if items else None,
        "reason": None if items else "取得した本文に識別可能な受け入れ条件チェックリストがありません",
    }


def _checkboxes(body):
    section_level, fence = None, None
    items = []
    for number, line in enumerate(body.splitlines(), start=1):
        marker = FENCE.fullmatch(line)
        if marker and fence is None:
            fence = marker[1]
            continue
        if fence is not None:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        heading = HEADING.match(line)
        if heading:
            level = len(heading[1])
            if AC_TITLE.match(heading[2].strip("*[] ")):
                section_level = level
            elif section_level is not None and level <= section_level:
                section_level = None
        elif section_level is not None and (item := CHECKBOX.match(line)):
            items.append({"line": number, "text": item[2], "checked": item[1].lower() == "x"})
    return items
