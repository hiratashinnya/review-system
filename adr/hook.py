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
            roots.update(command_roots(command, Path(payload.get("cwd") or ".")))
        except ValueError:
            continue
    pending = []
    for root in roots:
        for data, _ in load(root):
            if data["decision"]["tracking_status"] == "pending":
                pending.append(data["id"])
    return {"systemMessage": "ADR: Issue未起票: " + ", ".join(sorted(set(pending)))} if pending else {}


def command_roots(command, cwd):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace = " \t\r"
    tokens, segment, roots = list(lexer), [], set()
    for token in [*tokens, ";"]:
        if token and all(char in ";&|()\n" for char in token):
            if segment[:1] == ["cd"]:
                arguments = [part for part in segment[1:] if part != "--"]
                if len(arguments) == 1:
                    cwd = (cwd / arguments[0]).resolve()
            for position in range(len(segment) - 2):
                if segment[position:position + 2] != ["-m", "adr"]:
                    continue
                tail = segment[position + 2:]
                if tail[0] not in ("new-entry", "file-issue"):
                    continue
                for index, argument in enumerate(tail):
                    if argument == "--root" and index + 1 < len(tail):
                        roots.add(cwd / tail[index + 1])
                    elif argument.startswith("--root="):
                        roots.add(cwd / argument.split("=", 1)[1])
            segment = []
        else:
            segment.append(token)
    return roots


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
