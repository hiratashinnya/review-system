"""申し送りコメントの生成と解析。"""

import re

from .finding_handoff_hash import content_hash, normalize_text
from .finding_handoff_keys import HANDOFF_HASH_VERSION
from .vocabulary import FINDING_ID_RE, HARM_LEVELS

START = "<!-- karte-handoff:v1 -->"
END = "<!-- /karte-handoff -->"
FIELDS = ("finding", "harm", "summary", "locus", "expected", "hash_version", "content_hash")
AGENTS = ("Claude Code", "Codex")


def render_block(finding, agent: str) -> str:
    if agent not in AGENTS:
        raise ValueError("不正な agent")
    values = [finding.id, finding.harm, finding.summary, ", ".join(sorted(finding.locus)),
              finding.expected, str(HANDOFF_HASH_VERSION),
              content_hash(finding.id, finding.harm, finding.summary, finding.locus, finding.expected)]
    if any("\n" in normalize_text(value) or "\r" in value for value in values):
        raise ValueError("handoff の項目に改行は使えません")
    return "\n".join([START, f"{agent} (AI) による転記（karte handoff）",
                      *(f"- {key}: {normalize_text(value)}" for key, value in zip(FIELDS, values)), END])


def parse_block(body: str) -> dict | None:
    body = normalize_text(body)
    if body.count(START) != 1 or body.count(END) != 1:
        return None
    start, end = body.find(START), body.find(END)
    if (end < start or (start and body[start - 1] != "\n")
            or (end + len(END) < len(body) and body[end + len(END)] != "\n")):
        return None
    lines = body[start:end + len(END)].split("\n")
    if len(lines) != len(FIELDS) + 3 or lines[0] != START or lines[-1] != END:
        return None
    if lines[1] not in tuple(f"{agent} (AI) による転記（karte handoff）" for agent in AGENTS):
        return None
    result = {}
    for key, line in zip(FIELDS, lines[2:-1]):
        prefix = f"- {key}: "
        if key == "locus" and line == "- locus:":
            result[key] = ""
        elif line.startswith(prefix):
            result[key] = line[len(prefix):].strip()
        else:
            return None
    if result["hash_version"] != str(HANDOFF_HASH_VERSION):
        return None
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", result["content_hash"]):
        return None
    if not FINDING_ID_RE.fullmatch(result["finding"]) or result["harm"] not in HARM_LEVELS:
        return None
    if any(not result[key] for key in ("summary", "expected")):
        return None
    result["locus"] = [item.strip() for item in result["locus"].split(",") if item.strip()]
    return result
