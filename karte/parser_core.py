"""parser_core の責務。詳細は .ai/rationale/karte-module-split.md。"""
import argparse
from .parser_ingest_args import register_ingest
from .parser_attempt_args import register_append, register_close_attempt
from .parser_inspect_args import register_render, register_check, register_status
from .verb_boundary import require_declared

def build_parser(extra_registrars=()) -> argparse.ArgumentParser:
    """組込みと追加 verb のパーサを構築する。"""
    parser = argparse.ArgumentParser(
        prog="karte",
        description="是正ループの診断カルテ（tmp/_karte/issue-<N>.md）を操作する",
    )
    subparsers = parser.add_subparsers(dest="verb", required=True)

    def add_issue(sub):
        sub.add_argument("--issue", help="Issue 番号（省略時は tmp/_karte/active.json）")

    register_ingest(subparsers, add_issue)
    register_render(subparsers, add_issue)
    register_append(subparsers, add_issue)
    register_close_attempt(subparsers, add_issue)
    register_check(subparsers, add_issue)
    register_status(subparsers, add_issue)
    for register in extra_registrars:
        register(subparsers, add_issue)
    require_declared(subparsers)
    return parser
