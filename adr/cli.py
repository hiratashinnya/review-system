"""ADR の read-only view と CLI dispatch。"""
import datetime
import json
import sys
from dsv2 import query
from .check import check
from .cli_parser import parser
from .cli_write import file_issue, new_entry
from .github import stale
from .index import index
from .store import load


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.verb == "new-entry":
            new_entry(args)
            return 0
        if args.verb == "file-issue":
            file_issue(args)
            return 0
        if args.verb == "check":
            errors = check(args.root, args.repo, base=args.base,
                           require_base=args.require_base, envelopes=args.envelope)
            for error in errors:
                print(error, file=sys.stderr)
            return int(bool(errors))
        if args.verb in ("deps", "dependents", "orphans", "index"):
            meta = index(args.root, args.repo, args.envelope)
            if args.verb == "index":
                output = meta
            elif args.verb == "orphans":
                output = query.orphans(meta)
            else:
                output = getattr(query, args.verb)(meta, args.id)
                if output is None:
                    raise ValueError("ADR が存在しない")
        else:
            records = load(args.root)
            replaced = {data["supersedes"] for data, _ in records if data["supersedes"]}
            if args.verb == "stale":
                output = stale(records, args.repo, args.days)
            else:
                output = [dict(data, derived_status=("superseded" if data["id"] in replaced
                                                    else "active"))
                          for data, _ in records if args.verb != "todo"
                          or data["decision"]["tracking_status"] == "pending"]
        print(json.dumps(output, ensure_ascii=False, default=str, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"adr: {exc}", file=sys.stderr)
        return 1
