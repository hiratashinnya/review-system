"""工程artifactのread-only CLI。"""
import argparse
import json
from .check import check
from .query import index, deps, dependents, orphans
from .store import load


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "index", "show", "deps", "dependents", "orphans"))
    parser.add_argument("--repo", default=".")
    parser.add_argument("--id")
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            errors = check(args.repo)
            print("\n".join(errors) if errors else "issue_envelope: clean")
            return bool(errors)
        if args.command in ("index", "deps", "dependents", "orphans"):
            meta = index(args.repo)
            if args.command in ("deps", "dependents") and not args.id:
                raise ValueError("deps/dependentsには--idが必須")
            queries = {"index": lambda: meta, "orphans": lambda: orphans(meta),
                       "deps": lambda: deps(meta, args.id),
                       "dependents": lambda: dependents(meta, args.id)}
            payload = queries[args.command]()
        else:
            payload = [data for data, _ in load(args.repo) if not args.id or data["id"] == args.id]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(str(exc))
        return 1
