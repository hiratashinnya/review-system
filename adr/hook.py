"""PostToolUse の ADR pending 通知。助言専用、失敗時は診断して継続。"""
import json
import shlex
import sys
from pathlib import Path
from karte_notify.notify import extract_commands
from .store import load


def notification(payload):
    roots = set()
    for command in extract_commands(payload.get("tool_name", ""), payload.get("tool_input", {})):
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        for position in range(len(tokens) - 2):
            if tokens[position:position + 2] != ["-m", "adr"]:
                continue
            tail = tokens[position + 2:]
            if not tail or tail[0] not in ("new-entry", "file-issue"):
                continue
            if "--root" in tail:
                index = tail.index("--root") + 1
                if index < len(tail):
                    roots.add(tail[index])
            roots.update(token.split("=", 1)[1] for token in tail if token.startswith("--root="))
    pending = []
    cwd = Path(payload.get("cwd") or ".")
    for root in roots:
        for data, _ in load(cwd / root):
            if data["decision"]["tracking_status"] == "pending":
                pending.append(data["id"])
    return {"systemMessage": "ADR: Issue未起票: " + ", ".join(sorted(set(pending)))} if pending else {}


def main():
    try:
        result = notification(json.load(sys.stdin))
        if result:
            print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        print(f"adr-notify: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
