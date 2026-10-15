"""停止 template の限定 YAML 形式を検査し、曖昧なキーを拒否する。"""

import json
import re


def stopped_frontmatter(body):
    sections = body.split("---\n", 2)
    if not body.startswith("---\n") or len(sections) != 3:
        return False
    entries = {}
    for line in sections[1].splitlines():
        if re.fullmatch(r"  - [a-z_]+", line):
            if "tools" not in entries:
                return False
            continue
        match = re.fullmatch(r"(name|description|tools|disable-model-invocation|user-invocable): ?(.*)", line)
        if not match or match[1] in entries:
            return False
        entries[match[1]] = match[2]
    if entries.get("disable-model-invocation") != "true" or entries.get("user-invocable") != "false":
        return False
    if "tools" in entries and entries["tools"] != "":
        return False
    if "name" in entries and not re.fullmatch(r"[a-z][a-z0-9-]*", entries["name"]):
        return False
    description = entries.get("description", "")
    if re.fullmatch(r"'(?:[^']|'')*'", description):
        return True
    try:
        return isinstance(json.loads(description), str)
    except ValueError:
        return False
