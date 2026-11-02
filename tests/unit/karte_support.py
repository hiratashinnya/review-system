"""karte のテスト共通の足場（一時 repo-root・finding の欄・レポート・CLI 実行・writer lock 判定）。"""

import contextlib
import fcntl
import io
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, cast
from unittest import mock

from karte import cli, model, paths

# finding の必須欄のうち、指摘ごとに変える ``locus`` / ``summary`` を除いたもの。
FINDING_FIELDS = {
    "harm": "real",
    "harm_detail": "検証が素通りして誤った取り込みが通る",
    "severity": "major",
    "scope": "in",
    "evidence": "a/b.py:1 を読み、検査が無いのを確認",
    "expected": "検査が働く",
    "recheck": "該当入力で拒否されることを確認する",
}


def finding(locus: str, summary: str, **overrides) -> dict:
    """``FINDING_FIELDS`` に ``locus`` / ``summary`` と上書きを足した 1 件分の欄。"""
    return {**FINDING_FIELDS, "locus": locus, "summary": summary, **overrides}


def verb_parsers(parser) -> dict:
    """``cli.build_parser`` が組み立てた parser の ``{verb 名: その subparser}``。"""
    action = next(a for a in parser._actions if a.dest == "verb")
    return dict(cast(Any, action).choices)


def required_finding(karte: model.Karte, finding_id: str) -> model.Finding:
    """台帳の finding を返す。無ければテストを失敗させる（``None`` を属性アクセスさせない）。"""
    found = karte.finding(finding_id)
    if found is None:
        raise AssertionError(f"台帳に {finding_id} が無い")
    return found


def report_text(*blocks) -> str:
    """``(title, fields)`` の列から ``### <title>`` ブロック列のレビューレポート本文を組み立てる。"""
    parts = []
    for title, fields in blocks:
        lines = [f"### {title}", *(f"{key}: {value}" for key, value in fields.items())]
        parts.append("\n".join(lines))
    return "\n\n".join(parts) + "\n"


def make_tmp_repo(case, prefix: str = "karte-", *, with_tmp: bool = True) -> Path:
    """一時 repo-root を作り、テスト終了時に消す。``with_tmp`` で ``tmp/`` も作る。"""
    root = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    case.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
    if with_tmp:
        (root / "tmp").mkdir()
    return root


def run_cli(root, argv, stdin_text: str = ""):
    """``build_parser`` で解釈した ``argv`` を ``root`` に対して実行し、``(終了コード, 標準出力, 標準エラー)``。"""
    args = cli.build_parser().parse_args(argv)
    args.repo_root = str(root)
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(sys, "stdin", io.StringIO(stdin_text)):
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = args.func(args)
    return code, out.getvalue(), err.getvalue()


def writer_lock_is_held(repo_root) -> bool:
    """別の file description から非ブロッキングで取りに行き、取れなければ誰かが握っている。"""
    lock_path = paths.karte_dir(repo_root, create=True) / ".writer.lock"
    with open(lock_path, "a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle, fcntl.LOCK_UN)
        return False
