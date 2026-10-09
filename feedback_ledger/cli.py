"""`python3 -m feedback_ledger …` CLI compatibility API."""

from __future__ import annotations

import sys
from pathlib import Path

from . import paths as paths_module
from . import schema as schema_module
from . import status as status_module
from .check import (
    check_canonical, check_id_references, check_paths_exist, check_proposals,
    check_triage, run_checks,
)
from .cli_commit import _commit, _load_and_validate, _preflight
from .cli_entry import cmd_new_entry
from .cli_parser import build_parser
from .cli_proposal_create import cmd_amend_proposal, cmd_propose
from .cli_proposal_decision import (
    _decide, cmd_apply_done, cmd_approve, cmd_reject,
)
from .cli_reports import cmd_check, cmd_index, cmd_render, cmd_status
from .cli_support import (
    EXIT_ERROR, EXIT_NOT_FOUND, EXIT_OK, TRIAGE_DRAFT_TEMPLATE_VERDICT,
    _errors, _fail, _parse_date, _print, _require_proposal,
)
from .cli_triage import cmd_triage_close, cmd_triage_open
from .model import ERROR, WARN, DocumentError, Finding
from .paths import FeedbackMissing, FeedbackPathError
from .render import RenderError, render_ledger
from .schema import PROPOSAL_SPEC, SPECS, TRIAGE_SPEC
from .store import Document, canonical_text, load_draft, load_store, write_document


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.root = Path(args.root).resolve() if args.root else paths_module.repo_root()
    try:
        return args.func(args)
    except FeedbackMissing as exc:
        print(f"NOT_FOUND: {exc}", file=sys.stderr)
        return EXIT_NOT_FOUND
    except (FeedbackPathError, DocumentError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
