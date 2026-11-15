"""PostToolUse の ADR pending 通知。助言専用、失敗時は診断して継続。"""
import json
import sys
from pathlib import Path
from karte_notify.trigger import SUPPORTED_TOOL_NAMES
from .store import load
from .notice_roots import registered_roots, response_roots


def notification(payload):
    if payload.get("tool_name") not in SUPPORTED_TOOL_NAMES:
        return {}
    registered = registered_roots(Path(payload.get("cwd") or "."))
    observed = response_roots(payload.get("tool_response"))
    roots = [*sorted(registered & observed), *sorted(registered - observed)]
    pending = []
    for root in roots:
        try:
            records = load(root)
        except (ValueError, OSError) as exc:
            print(f"adr-notify: {root}: {exc}", file=sys.stderr)
            continue
        for data, _ in records:
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
