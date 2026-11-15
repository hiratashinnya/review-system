"""parser_attempt_args の責務。詳細は .ai/rationale/karte-module-split.md。"""
from . import model
from .verb_append import cmd_append
from .verb_close_attempt import cmd_close_attempt

def register_append(subparsers, add_issue):
    append = subparsers.add_parser("append", help="Attempt を追記（類似飽和なら拒否）")
    add_issue(append)
    append.add_argument("--round", help="ラウンド番号（省略時は進行ポインタ）")
    append.add_argument("--finding-ids", nargs="+", required=True, help="対象の finding ID")
    append.add_argument("--root-cause", required=True, help="根本原因仮説の slug")
    append.add_argument(
        "--change-kind", required=True, choices=list(model.CHANGE_KINDS), help="変更の種類"
    )
    append.add_argument("--targets", nargs="+", required=True, help="触る関数/クラス（file::symbol）")
    append.add_argument("--diagnosis", default="", help="診断の要約（1行）")
    append.set_defaults(func=cmd_append)


def register_close_attempt(subparsers, add_issue):
    close = subparsers.add_parser("close-attempt", help="実測 touched-set を Result として追記")
    add_issue(close)
    close.add_argument(
        "--attempt",
        help=(
            "対象 Attempt 番号（省略時: 未クローズの Attempt が1つならそれを使う。"
            "2つ以上あれば曖昧なので明示を要求して拒否する。0（Attempt が1件も無い、"
            "または全件クローズ済み）でも同様に明示を要求して拒否する＝Issue #378）"
        ),
    )
    close.add_argument(
        "--outcome", required=True, choices=list(model.OUTCOMES), help="処置結果"
    )
    close.add_argument("--finding-ids", nargs="+", help="省略時は Attempt の finding_ids")
    close.add_argument(
        "--base",
        default="HEAD",
        help=(
            "git diff の比較先（既定 HEAD）。commit・push 後は作業ツリーが HEAD と一致し"
            "diff が空になる——その場合は変更前の commit（例 HEAD~1）を明示するか"
            "--diff-file を使う。診断せず空 diff で fixed/partial 等を記録することは"
            "できない（--outcome no-change の場合のみ例外＝Issue #355）"
        ),
    )
    close.add_argument("--diff-file", help="git を呼ばず既存の diff ファイルから算出する")
    close.add_argument("--note", default="", help="結果の補足（1行）")
    close.set_defaults(func=cmd_close_attempt)
