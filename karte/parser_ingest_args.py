"""parser_ingest_args の責務。詳細は .ai/rationale/karte-module-split.md。"""
from .report_source import STDIN_SOURCE
from .verb_ingest_review import cmd_ingest_review

def register_ingest(subparsers, add_issue):
    ingest = subparsers.add_parser("ingest-review", help="レビューレポートを台帳へ取り込む")
    add_issue(ingest)
    ingest.add_argument(
        "--round",
        help="レビューのラウンド番号（原則単調増加、保護モードは最新と同値も可。省略時は tmp/_karte/active.json の次）",
    )
    ingest.add_argument(
        "--from",
        dest="source",
        required=True,
        help=f"レビューレポートのパス（`{STDIN_SOURCE}` で標準入力から読む）",
    )
    ingest.set_defaults(func=cmd_ingest_review)
