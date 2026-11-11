"""カルテ CLI の入口。全文は .ai/rationale/karte-module-split.md の K-04 移設節。

verb:
  ingest-review: レビューを取り込む。
  render: 試行と未解消 finding を表示する。
  append: Attempt を追記する。
  close-attempt: 実測結果を追記する。
  check: 診断網羅とクローズを検査する。
  status: 進捗を判定する。
終了コード: 0 OK、2 未検出、3 飽和、4 前提違反、5 取り込み済み未完了。
進行ポインタは各 verb の issue と ingest-review・append・check の round を補完する。
ingest-review は記録済みの次の round、append と check は記録済み round を使う。
ingest-review と check は必要なポインタが無効なら拒否する。append の round は
欠落や issue 不一致なら台帳へ縮退するが、不正値は拒否する。
"""

from __future__ import annotations

import argparse
import json
import sys

from . import (
    active_pointer,
    ingest_review,
    int_args,
    karte_loader,
    model,
    paths,
    pointer_completion,
    repo_roots,
    similarity,
)
from . import touched as touched_mod
from .errors import KarteUsageError
from .exit_codes import EXIT_ERROR, EXIT_OK, EXIT_SATURATED
from .render_text import render_lines
from .saturation_groups import group_directive as _group_directive
from .saturation_groups import priors_for as _priors_for
from .saturation_groups import saturated_groups as _saturated_groups
from .stall_detection import STALL_ROUNDS as STALL_ROUNDS
from .stall_detection import stalled_ids as _stalled_ids
from .status_payload import status_payload as _status_payload
from .status_text import status_lines
from .utf8_text import read_stream_text
from .verb_boundary import fail_close, require_declared

from .report_source import STDIN_SOURCE, read_report as _read_report
from .close_attempt_target import resolve_close_attempt_number as _resolve_close_attempt_number, validate_outcome as _validate_outcome
from .verb_ingest_review import prepare_ingest as _prepare_ingest, cmd_ingest_review
from .verb_append import cmd_append
from .verb_close_attempt import cmd_close_attempt
from .verb_check import cmd_check
from .verb_show import cmd_render, cmd_status
from .parser_core import build_parser


def main(argv=None, extra_registrars=()) -> int:
    """パーサから verb を呼び出す。"""
    args = build_parser(extra_registrars).parse_args(argv)
    return args.func(args)
