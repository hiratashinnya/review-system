"""Read-only checks and validated writer commands; exit 0 / 2 / 4."""

import json
import sys

from .catalog import check_catalog, load_catalog, read_raw
from .cli_actions import write_action
from .cli_parser import parser
from .gitbase import compare_to_base
from .serialization import render
from .storage import sha
from .views import entries


def execute(args) -> tuple[int, object]:
    root = args.root.resolve()
    if args.action in ("new", "amend", "transition", "promote"):
        return 0, write_action(args)
    catalog = load_catalog(root)
    if args.action == "check":
        if args.require_base and not args.against_ref:
            raise ValueError("--require-base requires --against-ref")
        errors = check_catalog(catalog, canonical=True, raw_files=read_raw(root))
        if args.against_ref:
            drift, remote = compare_to_base(root, catalog, args.against_ref)
            errors += drift + check_catalog({**remote, **catalog})
        return (4 if errors else 0), {"errors": sorted(set(errors)), "count": len(catalog)}
    errors = check_catalog(catalog, canonical=True, raw_files=read_raw(root))
    if errors:
        raise ValueError("; ".join(errors))
    if args.action == "show":
        if args.id not in catalog:
            return 2, {"error": "advisory not found: " + args.id}
        doc = catalog[args.id]
        return 0, {"entry": doc, "sha256": sha(render(doc).encode("utf-8"))}
    if args.action == "list":
        return 0, {"items": entries(catalog, args.today, args.stale_days)}
    raise ValueError("unknown read action")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        status, output = execute(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        status, output = 4, {"errors": [str(exc)]}
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True),
          file=sys.stderr if status else sys.stdout)
    return status
