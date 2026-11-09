"""検査後に `codex exec` を起動する。

通常ロールはCodex終了コードを透過する。pr-reviewerは出力を透過せず、Codex実行と
karte取り込みの成功を0、失敗を2で返す。検査拒否も2、timeoutは124。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping, Sequence

from karte import paths

from .arguments import parse_request
from .artifact_binding import verify_artifact_binding
from .errors import CodexExecError
from .invocation import build_codex_argv, compose_prompt
from .launcher import run_codex
from .nesting_guard import refuse_nested_launch
from .profile_pin import verify_profile_pinned
from .project_trust import codex_home, verify_project_trusted
from .prompt_files import read_prompt, resolve_output_target
from .review_binding import review_envelope_of
from .review_handoff import ingest_codex_output
from .review_target import capture_target
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
    expected_issue = verify_artifact_binding(request, cwd, worktree)
    body = read_prompt(request.prompt_file, cwd, worktree)
    output_file = resolve_output_target(request.output_file, cwd, worktree)
    is_reviewer = request.role == "pr-reviewer"
    launch_target = envelope = None
    if is_reviewer and output_file.exists():
        raise CodexExecError("CODEX_EXEC_OUTPUT_INVALID", "pr-reviewer output file must be new")
    if is_reviewer:
        launch_target = capture_target(
            paths.main_worktree_root(worktree), expected_issue
        )
        envelope = review_envelope_of(cwd, request.binding_file)
    result = run_codex(
        build_codex_argv(request, worktree, output_file, codex),
        compose_prompt(request.role, worktree, body),
        cwd=worktree,
        timeout_seconds=request.timeout_seconds,
        environ=environ,
        quiet=is_reviewer,
    )
    if not is_reviewer:
        return result
    print(ingest_codex_output(worktree, output_file, expected_issue, launch_target, envelope))
    return 0


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
