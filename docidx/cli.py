"""docidx の CLI（``python -m docidx ...``）。

サブコマンド: index / search / show / deps / dependents。
``--format json|table``（既定 json）。終了コード: 0 正常 / 2 未検出 / 3 用法。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import query, render, scan

EXIT_OK = 0
EXIT_NOT_FOUND = 2
EXIT_USAGE = 3


def _build(args: argparse.Namespace):
    root = Path(args.root).resolve() if args.root else scan.find_repo_root()
    config = Path(args.config).resolve() if args.config else None
    return scan.build_index(repo_root=root, config_path=config)


def _emit_json(obj) -> None:
    print(render.to_json(obj))


def cmd_index(args) -> int:
    index = _build(args)
    nodes = list(index.nodes)
    if args.format == "json":
        _emit_json([n.summary_row() for n in nodes])
    else:
        print(render.index_table(nodes))
        print(f"\n{len(nodes)} ノード")
    return EXIT_OK


def cmd_search(args) -> int:
    index = _build(args)
    hits = query.search(
        index,
        node_type=args.type,
        label=args.label,
        id_glob=args.id,
        text=args.text,
    )
    if args.format == "json":
        _emit_json([n.summary_row() for n in hits])
    else:
        print(render.search_table(hits))
        print(f"\n{len(hits)} 件")
    return EXIT_OK


def cmd_show(args) -> int:
    index = _build(args)
    missing = [nid for nid in args.ids if nid not in index.by_id]
    found = [index.by_id[nid] for nid in args.ids if nid in index.by_id]
    if args.format == "json":
        _emit_json([n.to_dict() for n in found])
    else:
        for i, node in enumerate(found):
            if i:
                print("\n" + "=" * 60 + "\n")
            print(render.show_text(node))
    if missing:
        print(f"未検出: {', '.join(missing)}", file=sys.stderr)
        return EXIT_NOT_FOUND
    return EXIT_OK


def cmd_deps(args) -> int:
    index = _build(args)
    if args.id not in index.by_id:
        print(f"未検出: {args.id}", file=sys.stderr)
        return EXIT_NOT_FOUND
    rows = query.deps(index, args.id)
    if args.format == "json":
        _emit_json({"id": args.id, "deps": rows})
    else:
        print(render.deps_table(args.id, rows))
    return EXIT_OK


def cmd_dependents(args) -> int:
    index = _build(args)
    if args.id not in index.by_id:
        print(f"未検出: {args.id}", file=sys.stderr)
        return EXIT_NOT_FOUND
    rows = query.dependents(index, args.id)
    if args.format == "json":
        _emit_json({"id": args.id, "dependents": rows})
    else:
        print(render.dependents_table(args.id, rows))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    # 共通オプション（サブコマンドの前後どちらでも指定できるよう parent にする）
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="リポジトリ root（既定: doc-system/ を上方向に自動検出）")
    common.add_argument(
        "--config", help="config.yaml のパス（既定: <root>/docs/doc-system/config.yaml）"
    )
    common.add_argument(
        "--format", choices=["json", "table"], default="json", help="出力形式（既定 json）"
    )

    parser = argparse.ArgumentParser(
        prog="docidx",
        parents=[common],
        description="doc-system のノードを検索・読み込みする md2idx 風ツール",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", parents=[common], help="全ノードの軽量インデックス（目次）")
    p_index.set_defaults(func=cmd_index)

    p_search = sub.add_parser("search", parents=[common], help="型/ラベル/ID/キーワードで検索")
    p_search.add_argument("--type", help="ノード型（FR, SPEC, FND ...）")
    p_search.add_argument("--label", help="labels に含まれるタグ")
    p_search.add_argument("--id", help="ID グロブ（例: SPEC-1-*）")
    p_search.add_argument("--text", help="見出し＋本文のキーワード（大小無視）")
    p_search.set_defaults(func=cmd_search)

    p_show = sub.add_parser("show", parents=[common], help="ノード全体を読み込む（yaml＋本文）")
    p_show.add_argument("ids", nargs="+", help="ノード ID（複数可）")
    p_show.set_defaults(func=cmd_show)

    p_deps = sub.add_parser("deps", parents=[common], help="依存先（出辺）＋ドリフト")
    p_deps.add_argument("id", help="ノード ID")
    p_deps.set_defaults(func=cmd_deps)

    p_dependents = sub.add_parser("dependents", parents=[common], help="依存元（入辺・逆引き）")
    p_dependents.add_argument("id", help="ノード ID")
    p_dependents.set_defaults(func=cmd_dependents)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BrokenPipeError:
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
