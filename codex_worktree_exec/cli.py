"""検査を順に通し、すべて通ったときだけ `codex exec` を起動する。

検査に通らなければ `codex_worktree_exec: <識別子>: <詳細>` を stderr に1行出して 2 を返す。
timeout は 124、起動できた場合は Codex の終了コードをそのまま返す。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping, Sequence

from .arguments import parse_request
from .errors import CodexExecError
from .invocation import build_codex_argv, compose_prompt
from .launcher import run_codex
from .nesting_guard import refuse_nested_launch
from .profile_pin import verify_profile_pinned
from .project_trust import codex_home, verify_project_trusted
from .prompt_files import read_prompt, resolve_output_target
from .worktree_binding import bind_worktree

EXIT_REFUSED = 2
EXIT_TIMEOUT = 124


def _launch(
    argv: Sequence[str], environ: Mapping[str, str], cwd: Path, codex: str
) -> int:
    request = parse_request(argv)
    refuse_nested_launch(environ)
    worktree = bind_worktree(request.worktree, cwd)
    verify_profile_pinned(worktree, request.role)
    verify_project_trusted(worktree, codex_home(environ))
    body = read_prompt(request.prompt_file, cwd)
    output_file = resolve_output_target(request.output_file, cwd)
    return run_codex(
        build_codex_argv(request, worktree, output_file, codex),
        compose_prompt(request.role, worktree, body),
        cwd=worktree,
        timeout_seconds=request.timeout_seconds,
        environ=environ,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    codex: str = "codex",
) -> int:
    try:
        return _launch(
            sys.argv[1:] if argv is None else argv,
            os.environ if environ is None else environ,
            Path.cwd() if cwd is None else cwd,
            codex,
        )
    except CodexExecError as error:
        print(f"codex_worktree_exec: {error}", file=sys.stderr)
        return EXIT_TIMEOUT if error.error_id == "CODEX_EXEC_TIMEOUT" else EXIT_REFUSED
