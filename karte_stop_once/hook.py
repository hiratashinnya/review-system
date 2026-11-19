"""Claude PostToolUse arms one STOP event; next wrong tool is denied once."""
import json
import os
import sys
from pathlib import Path

from . import decision, state, trigger


def _root(root):
    if root is not None:
        return Path(root)
    from karte.paths import main_worktree_root
    return main_worktree_root(os.environ["CLAUDE_PROJECT_DIR"])


def _status(root, issue):
    from karte.karte_loader import load_karte
    from karte.status_payload import status_payload
    return status_payload(load_karte(root, issue)[1], root)


def run(kind, payload, *, root=None, status_reader=None):
    """Pure hook response; invalid/non-target payloads do not arm other sessions."""
    if not isinstance(payload, dict) or not isinstance(payload.get("session_id"), str):
        return None
    session = payload["session_id"]
    if kind == "post":
        issue = trigger.issue_from_result(payload)
        if issue is None:
            return None
        base = _root(root)
        value = (status_reader or _status)(base, issue)
        event = decision.evaluate(value)
        if state.arm(base, session, event) and event:
            return {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                    "additionalContext": decision.instruction(event)}}
    elif kind == "pre":
        base = _root(root)
        event = state.attempt(base, session, payload.get("tool_name", ""))
        if event:
            return {"hoookSpecificOutput": {"hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": decision.instruction(event)}}
    return None


def main(argv=None):
    kind = (argv or sys.argv[1:])[0]
    if kind not in ("pre", "post"):
        return 2
    try:
        response = run(kind, json.load(sys.stdin))
        if response:
            print(json.dumps(response, ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        # Trial only: cannot turn a hook failure into a session-wide permanent STOP.
        print(f"karte_stop_once: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
