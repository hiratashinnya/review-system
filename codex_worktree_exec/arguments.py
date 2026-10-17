"""CLI 引数を検査して `ExecRequest` を返す。

`-c` は引数に持たせない（全ロール共通の deny 層が `python3` と `-c` の組を拒否する）。
`--role` の値と呼び出し元ロールの一致は `.claude/hooks/agent-command-gate.sh` が見る（D4）。
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Sequence

from .errors import CodexExecError
from .request import ExecRequest
from .roles import CODEX_EXEC_ROLES

REASONING_EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
DEFAULT_TIMEOUT_SECONDS = 540
MAX_TIMEOUT_SECONDS = 3600


class _StoreOnce(argparse.Action):
    """同じ option の2回目を拒否する（後勝ちで別ロールへ差し替わる経路を作らない）。"""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            parser.error(f"{option_string} was given more than once")
        setattr(namespace, self.dest, values)


class _FailClosedParser(argparse.ArgumentParser):
    """argparse の usage 出力と exit を、識別子付きの例外へ置き換える。"""

    def error(self, message):
        raise CodexExecError("CODEX_EXEC_ARGUMENT_INVALID", message)


def _parser() -> argparse.ArgumentParser:
    parser = _FailClosedParser(
        prog="python3 -m codex_worktree_exec", allow_abbrev=False, add_help=False
    )
    for flag, dest, required in (
        ("--role", "role", True),
        ("-C", "worktree", True),
        ("--prompt-file", "prompt_file", True),
        ("--output-file", "output_file", True),
        ("--model", "model", True),
        ("--reasoning-effort", "reasoning_effort", True),
        ("--timeout-seconds", "timeout_seconds", False),
        ("--binding-file", "binding_file", False),
    ):
        parser.add_argument(flag, dest=dest, required=required, action=_StoreOnce)
    return parser


def _timeout_seconds(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_TIMEOUT_SECONDS
    if not raw.isdigit() or not 1 <= int(raw) <= MAX_TIMEOUT_SECONDS:
        raise CodexExecError("CODEX_EXEC_TIMEOUT_INVALID", raw)
    return int(raw)


def parse_request(argv: Sequence[str]) -> ExecRequest:
    """引数を検査する。許可外のロール・モデル名・推論予算・timeout は個別の識別子で拒否する。"""
    args = _parser().parse_args(list(argv))
    if args.role not in CODEX_EXEC_ROLES:
        raise CodexExecError("CODEX_EXEC_ROLE_NOT_ALLOWED", args.role)
    if not MODEL_RE.fullmatch(args.model):
        raise CodexExecError("CODEX_EXEC_MODEL_INVALID", args.model)
    if args.reasoning_effort not in REASONING_EFFORTS:
        raise CodexExecError("CODEX_EXEC_EFFORT_INVALID", args.reasoning_effort)
    return ExecRequest(
        role=args.role,
        worktree=Path(args.worktree),
        prompt_file=Path(args.prompt_file),
        output_file=Path(args.output_file),
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        timeout_seconds=_timeout_seconds(args.timeout_seconds),
        binding_file=Path(args.binding_file) if args.binding_file else None,
    )
