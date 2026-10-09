"""Read-only CLI commands for checks, state, index, and Markdown rendering."""

from __future__ import annotations

import datetime
import json
import sys

from . import status as status_module
from .check import run_checks
from .cli_support import EXIT_ERROR, EXIT_NOT_FOUND, EXIT_OK, _errors, _fail, _print
from .model import WARN
from .render import RenderError, render_ledger
from .schema import SPECS
from .store import load_store

def cmd_check(args) -> int:
    findings = run_checks(
        args.root,
        canonical=args.canonical,
        base_ref=args.base_ref,
        require_base=args.require_base,
    )
    _print(findings)
    errors = _errors(findings)
    warnings = [finding for finding in findings if finding.level == WARN]
    print(f"errors={len(errors)} warnings={len(warnings)}")
    return EXIT_ERROR if errors else EXIT_OK


def cmd_status(args) -> int:
    store = load_store(args.root)
    now = args.now or datetime.date.today()
    states = status_module.compute(store, now)
    if args.entry:
        states = [item for item in states if item.entry_id == args.entry]
        if not states:
            print(f"ERROR: 台帳エントリが見つからない: {args.entry}", file=sys.stderr)
            return EXIT_NOT_FOUND
    summary = status_module.summarize(states)
    if args.json:
        print(json.dumps(
            {"now": now.isoformat(),
             "summary": summary,
             "entries": [item.as_dict() for item in states]},
            ensure_ascii=False, sort_keys=True, indent=2,
        ))
        return EXIT_OK
    for item in states:
        mark = "STALE" if item.stale else "     "
        print(f"{mark} {item.entry_id}  {item.state}  since={item.since} "
              f"age={item.age_days}d  {item.detail}")
    print(f"total={summary['total']} stale={summary['stale']}")
    return EXIT_OK


def cmd_index(args) -> int:
    store = load_store(args.root)
    payload = {
        kind: [document.document_id for document in store.of(kind)]
        for kind in SPECS
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        for kind in sorted(payload):
            print(f"## {kind} ({len(payload[kind])})")
            for document_id in payload[kind]:
                print(f"  {document_id}")
    if not any(payload.values()):
        return EXIT_NOT_FOUND
    return EXIT_OK


def cmd_render(args) -> int:
    store = load_store(args.root)
    errors = _errors(store.findings)
    if errors:
        return _fail(errors)
    try:
        print(render_ledger(store), end="")
    except RenderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
