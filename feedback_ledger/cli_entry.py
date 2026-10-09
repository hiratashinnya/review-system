"""CLI command for creating immutable ledger entries."""

from __future__ import annotations

import sys
from pathlib import Path

from . import paths as paths_module
from . import schema as schema_module
from .cli_commit import _commit
from .cli_support import EXIT_ERROR, _errors, _fail, _print
from .model import ERROR, Finding, check_document_identity, normalize_document, parse_toml
from .schema import SPECS
from .schema_version import LEDGER_CURRENT_SCHEMA
from .store import load_store
from .identity_collisions import colliding_ledger_ids


def _load_current_entry(root, spec, draft):
    path = paths_module.draft_path(root, draft)
    relative = path.resolve().relative_to(Path(root).resolve()).as_posix()
    raw = parse_toml(paths_module.read_text(path))
    if isinstance(raw, dict) and raw.get("schema") != LEDGER_CURRENT_SCHEMA:
        return None, [Finding(
            "L1", ERROR, f"{relative}::schema",
            f"new-entry は現行版のみ受け付けます。schema を {LEDGER_CURRENT_SCHEMA} に直してください",
        )]
    data, findings = normalize_document(spec, raw, relative)
    if data is not None:
        findings.extend(check_document_identity(spec, data, relative))
    return data, findings


def cmd_new_entry(args) -> int:
    root = args.root
    spec = SPECS[schema_module.LEDGER]
    data, findings = _load_current_entry(root, spec, args.source)
    if data is None or _errors(findings):
        return _fail(findings)
    store = load_store(root)
    collisions = colliding_ledger_ids(
        data["id"], (entry.document_id for entry in store.of(schema_module.LEDGER))
    )
    if collisions:
        print(
            f"ERROR: [L1] id が既存の別エントリと NFKC+casefold 後に衝突: "
            f"{data['id']} / {', '.join(collisions)}",
            file=sys.stderr,
        )
        return EXIT_ERROR
    if store.by_id(schema_module.LEDGER, data["id"]) is not None:
        print(
            f"ERROR: [L6] 既存の台帳エントリは変更できない: {data['id']}"
            "（訂正は新しい id のエントリ＋supersedes で行う）",
            file=sys.stderr,
        )
        return EXIT_ERROR
    _print(findings)
    return _commit(root, spec, data)
