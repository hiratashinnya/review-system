"""CLI commands for opening and closing weekly triage records."""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

from . import paths as paths_module
from . import schema as schema_module
from . import status as status_module
from .cli_commit import _commit, _load_and_validate
from .cli_support import EXIT_ERROR, EXIT_OK, TRIAGE_DRAFT_TEMPLATE_VERDICT, _errors, _fail
from .schema import TRIAGE_SPEC
from .store import canonical_text, load_store

def cmd_triage_open(args) -> int:
    root = args.root
    now = args.now or datetime.date.today()
    match = schema_module.TRIAGE_ID_RE.match(f"TRG-{args.week}")
    if match is None:
        print(
            f"ERROR: --week は YYYY-Wnn の形で指定する: {args.week!r}", file=sys.stderr
        )
        return EXIT_ERROR
    year = int(match.group("year"))
    week = int(match.group("week"))
    try:
        start = datetime.date.fromisocalendar(year, week, 1)
        end = datetime.date.fromisocalendar(year, week, 7)
    except ValueError:
        print(f"ERROR: 実在しない ISO 週: {args.week}", file=sys.stderr)
        return EXIT_ERROR

    store = load_store(root)
    entries = status_module.untriaged_ids(store, now)
    data = {
        "schema": TRIAGE_SPEC.schema_const,
        "id": f"TRG-{args.week}",
        "period_start": start,
        "period_end": end,
        "reviewed": sorted(entries),
        "outcomes": [
            {
                "entry": entry_id,
                "verdict": TRIAGE_DRAFT_TEMPLATE_VERDICT,
                "proposal": "",
                "merged_into": "",
                "reason": "",
            }
            for entry_id in sorted(entries)
        ],
        "summary": {"notes": ""},
    }
    directory = paths_module.draft_dir(root, create=True)
    target = paths_module.resolve_within_repo(directory / f"TRG-{args.week}.toml", root)
    paths_module.write_text_atomic(target, canonical_text(TRIAGE_SPEC, data))
    print(f"OK: {target.relative_to(Path(root).resolve()).as_posix()}")
    print(f"棚卸し対象 {len(entries)} 件。verdict と reason を埋めて triage-close で確定する。")
    return EXIT_OK


def cmd_triage_close(args) -> int:
    root = args.root
    data, findings = _load_and_validate(root, TRIAGE_SPEC, args.source)
    if data is None or _errors(findings):
        return _fail(findings)
    return _commit(root, TRIAGE_SPEC, data)
