"""起動口: ``python3 -m draft_display {stop|notice}``（常に exit 0・fail-open）。"""

from __future__ import annotations

import sys
from pathlib import Path

from . import notice, stop

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_VERBS = {"stop": stop.run, "notice": notice.run}


def main(argv: list[str]) -> int:
    runner = _VERBS.get(argv[0]) if argv else None
    if runner is None:
        sys.stderr.write("usage: python3 -m draft_display {stop|notice}\n")
        return 0
    try:
        return runner(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, project_root=PROJECT_ROOT)
    except Exception as exc:  # fail-open: 可視化専用で作業を止めない
        sys.stderr.write(f"[draft-display] {type(exc).__name__}: {exc}\n")
        return 0


raise SystemExit(main(sys.argv[1:]))
