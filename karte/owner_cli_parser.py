"""主文脈専用 activate / decide のパーサー登録（実装から分離）。"""

from . import model

def register(subparsers, add_issue, cmd_activate, cmd_decide) -> None:
    activate = subparsers.add_parser("activate", help="進行ポインタを Issue に向ける（主文脈専用）")
    activate.add_argument("--issue", required=True, help="Issue 番号")
    activate.add_argument(
        "--repair-declared-scope", action="store_true",
        help="壊れた申告 scope の原本の行を除いて復旧する（元は .bak* に世代を分けて残す）",
    )
    for flag, text in (
        ("run-id", "review run の識別子"), ("target-key", "review 対象の識別子"),
        ("snapshot-oid", "レビュー対象の snapshot（40桁 OID）"),
        ("input-digest", "レビュー入力の sha256（64桁 hex）"), ("phase", "test_design | implementation"),
    ):
        activate.add_argument(f"--{flag}", help=f"review envelope の期待値: {text}（5 項目を同時に指定）")
    activate.add_argument("--ac-snapshot-file", help="dispatch時に取得した元Issue本文のローカルUTF-8ファイル（AC凍結）")
    activate.add_argument("--legacy-finding-only", action="store_true",
                          help="旧レビュー形式専用（AC判定なし・0件clean禁止）")
    activate.set_defaults(func=cmd_activate)
    decide = subparsers.add_parser("decide", help="オーナー決定を台帳へ記録する（主文脈専用）")
    add_issue(decide)
    decide.add_argument("--finding", required=True, help="対象の finding ID")
    decide.add_argument("--disposition", choices=list(model.DISPOSITIONS))
    decide.add_argument("--deferred-to")
    decide.add_argument("--waived-by")
    decide.add_argument("--waived-reason")
    decide.add_argument("--scope", help="オーナーが覆した scope（in|out）")
    decide.set_defaults(func=cmd_decide)
