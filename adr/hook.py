"""PostToolUse の ADR pending 通知。助言専用、失敗時は診断して継続。"""
import json
import sys
from pathlib import Path
from karte_notify.notify import extract_commands
from .store import load
from .shell_commands import command_roots


def notification(payload):
    roots = set()
    for command in extract_commands(payload.get("tool_name", ""), payload.get("tool_input", {})):
        try:
            roots.update(command_roots(command, Path(payload.get("cwd") or ".")))
        except ValueError:
            continue
    pending = []
    for root in roots:
        for data, _ in load(root):
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
