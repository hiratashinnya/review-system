"""CLI commands that create or replace proposal documents."""

from __future__ import annotations

import sys

from . import paths as paths_module
from . import schema as schema_module
from .cli_commit import _commit, _load_and_validate
from .cli_support import EXIT_ERROR, EXIT_NOT_FOUND, EXIT_OK, _errors, _fail, _require_proposal
from .schema import PROPOSAL_SPEC
from .store import load_store, write_document

def cmd_propose(args) -> int:
    root = args.root
    data, findings = _load_and_validate(root, PROPOSAL_SPEC, args.source)
    if data is None or _errors(findings):
        return _fail(findings)
    store = load_store(root)
    if store.by_id(schema_module.PROPOSAL, data["id"]) is not None:
        print(f"ERROR: 同じ id の改訂案が既にある: {data['id']}", file=sys.stderr)
        return EXIT_ERROR
    superseded = None
    if args.supersede:
        superseded = _require_proposal(store, args.supersede)
        if superseded is None:
            return EXIT_NOT_FOUND
        if superseded.data["status"] == "superseded":
            print(
                f"ERROR: [P1] 既に superseded の改訂案は再度 supersede できない: {args.supersede}",
                file=sys.stderr,
            )
            return EXIT_ERROR
    exit_code = _commit(root, PROPOSAL_SPEC, data)
    if exit_code != EXIT_OK or superseded is None:
        return exit_code
    replacement = dict(superseded.data)
    replacement["status"] = "superseded"
    with paths_module.writer_lock(root):
        write_document(root, PROPOSAL_SPEC, replacement)
    print(f"OK: {superseded.relpath} → status=superseded")
    return EXIT_OK


def cmd_amend_proposal(args) -> int:
    root = args.root
    data, findings = _load_and_validate(root, PROPOSAL_SPEC, args.source)
    if data is None or _errors(findings):
        return _fail(findings)
    store = load_store(root)
    current = _require_proposal(store, data["id"])
    if current is None:
        return EXIT_NOT_FOUND
    if current.data["status"] != "pending":
        print(
            f"ERROR: [P1] pending の改訂案だけを差し替えられる（現在: "
            f"{current.data['status']}）。決着済みの案は propose --supersede で置き換える",
            file=sys.stderr,
        )
        return EXIT_ERROR
    if data["status"] != "pending":
        print("ERROR: [P1] 差し替え後も status は pending でなければならない", file=sys.stderr)
        return EXIT_ERROR
    return _commit(root, PROPOSAL_SPEC, data)
