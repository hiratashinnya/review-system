"""dsv2 の CLI（``python3 -m dsv2 ...``）。

サブコマンド:
  * ``index``            nodes/** を走査し meta.json を生成（既定 ``<root>/meta.json``）。
  * ``deps <id>``        node の出辺（依存先）＋ドリフト情報。
  * ``dependents <id>``  node への入辺（依存元）。
  * ``orphans``          in/out 辺 0 本の完全孤立ノード。
  * ``drift``            ref_version が参照先バッジ x.y とドリフトしている辺（RULE-004）。
  * ``reverse <slug>``   FND 辺逆転（既定 dry-run・``--apply`` で書込＋git mv）。
  * ``rename <old> <new>`` slug 改題（既定 dry-run・``--apply`` で改名＋referrer 張替え）。
  * ``check-slug <slug>...`` 著作 slug のグローバル一意 fail-close 判定（Sub-D・DD-22）。
  * ``build-view``       meta.json ＋本文から単一 doc_view.html を生成（Sub-F #75）。

終了コード: 0 正常 / 2 未検出または用法エラー（argparse 既定） / 4 前提違反（reverse/rename の
前提不成立・**check-slug の衝突**）。
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from . import query, rename, reverse, viewer
from .meta import DEFAULT_ROOT, META_FILENAME, build_meta, duplicates, load_meta, write_meta
from .rename import RenameError
from .reverse import ReverseError

EXIT_OK = 0
EXIT_NOT_FOUND = 2  # 未検出。argparse の用法エラーも既定で 2 を返す
EXIT_ERROR = 4      # 前提違反（reverse/rename の前提不成立・check-slug の衝突＝fail-close）

# slug 正規化は doc-system-v2/slugify.py が唯一実装（独自再実装を禁じる・FORMAT.md §slug）。
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SLUGIFY_PY = _REPO_ROOT / "doc-system-v2" / "slugify.py"


def _load_slugify():
    """唯一実装 doc-system-v2/slugify.py を動的 import して slugify() を返す。"""
    spec = importlib.util.spec_from_file_location("_dsv2_slugify", _SLUGIFY_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.slugify


def _root(args) -> Path:
    return Path(args.root).resolve()


def _meta_path(args, root: Path) -> Path:
    return Path(args.meta).resolve() if args.meta else root / META_FILENAME


def _load(args):
    root = _root(args)
    meta = load_meta(root, _meta_path(args, root))
    for nid, locs in duplicates(meta).items():
        print(f"警告: id 重複 {nid}（{', '.join(locs)}）。先勝ちを採用。", file=sys.stderr)
    return root, meta


def cmd_index(args) -> int:
    root = _root(args)
    out = _meta_path(args, root)
    meta = write_meta(root, out)
    for nid, locs in duplicates(meta).items():
        print(f"警告: id 重複 {nid}（{', '.join(locs)}）。", file=sys.stderr)
    print(f"{len(meta['nodes'])} ノードを索引化 → {out}")
    return EXIT_OK


def cmd_deps(args) -> int:
    _root_, meta = _load(args)
    rows = query.deps(meta, args.id)
    if rows is None:
        print(f"未検出: {args.id}", file=sys.stderr)
        return EXIT_NOT_FOUND
    if not rows:
        print(f"{args.id}: 出辺なし")
        return EXIT_OK
    for r in rows:
        flags = []
        if not r["exists"]:
            flags.append("MISSING")
        if r["drift"] is True:
            flags.append("DRIFT")
        tag = f"  [{' '.join(flags)}]" if flags else ""
        print(f"{args.id} → {r['to']}  ref={r['ref_version'] or '-'} "
              f"target={r['target_version'] or '-'}{tag}")
    return EXIT_OK


def cmd_dependents(args) -> int:
    _root_, meta = _load(args)
    if args.id not in {n["id"] for n in meta["nodes"]}:
        print(f"未検出: {args.id}", file=sys.stderr)
        return EXIT_NOT_FOUND
    rows = query.dependents(meta, args.id)
    if not rows:
        print(f"{args.id}: 入辺なし（被参照ゼロ）")
        return EXIT_OK
    for r in rows:
        tag = "  [DRIFT]" if r["drift"] is True else ""
        print(f"{r['from']} ({r['type']}) → {args.id}  ref={r['ref_version'] or '-'}{tag}")
    return EXIT_OK


def cmd_orphans(args) -> int:
    _root_, meta = _load(args)
    orph = query.orphans(meta)
    if not orph:
        print("完全孤立ノードなし")
        return EXIT_OK
    for n in orph:
        print(f"{n['id']}  ({n['stage']}/{n['type']})  @ {n['yaml_path']}")
    print(f"\n{len(orph)} 件の完全孤立")
    return EXIT_OK


def cmd_drift(args) -> int:
    _root_, meta = _load(args)
    rows = query.drift(meta)
    if not rows:
        print("ドリフトなし")
        return EXIT_OK
    for r in rows:
        print(f"{r['from']} → {r['to']}  ref={r['ref_version']} ≠ target={r['target_version']}")
    print(f"\n{len(rows)} 件のドリフト（RULE-004）")
    return EXIT_OK


def cmd_reverse(args) -> int:
    root = _root(args)
    # 改変系はディスク現状を反映するため常にディスク走査で index を構築
    meta = build_meta(root)
    try:
        plan = reverse.plan_reverse(root, meta, args.slug)
    except ReverseError as ex:
        msg = str(ex)
        print(f"エラー: {msg}", file=sys.stderr)
        return EXIT_NOT_FOUND if "見つからない" in msg else EXIT_ERROR
    for n in plan.notes:
        print(f"[{args.slug}] {n}")
    if plan.noop:
        return EXIT_OK
    print(f"\n=== {args.slug}: 辺逆転計画 ===")
    for a in plan.actions:
        tag = {"normal": "backref 付与", "provenance": "provenance（記録のみ）",
               "missing": "付与先なし（記録のみ）"}[a.kind]
        if a.skipped_idempotent:
            tag = "backref 既存（冪等スキップ）"
        print(f"  →{a.to} [{a.kind}] {tag}")
    print(f"  DD-3: {plan.dd3_line}")
    if plan.notarget_line:
        print(f"  {plan.notarget_line}")
    for src, dst in plan.moves:
        print(f"  git mv {src} → {dst}")
    if args.apply:
        reverse.apply_reverse(root, plan)
        print(f"  適用済み（内容変更 {len(plan.new_text)} ファイル＋git mv {len(plan.moves)} 対）")
    else:
        print(plan.diff() or "  （差分なし）")
        print("\n（dry-run。書き込むには --apply を付けてください）")
    return EXIT_OK


def cmd_rename(args) -> int:
    root = _root(args)
    meta = build_meta(root)
    try:
        plan = rename.plan_rename(root, meta, args.old, args.new)
    except RenameError as ex:
        msg = str(ex)
        print(f"エラー: {msg}", file=sys.stderr)
        return EXIT_NOT_FOUND if "見つからない" in msg else EXIT_ERROR
    for n in plan.notes:
        print(f"[{args.old}] {n}")
    print(f"\n=== rename: {args.old} → {args.new} ===")
    for src, dst in plan.moves:
        print(f"  git mv {src} → {dst}")
    for rel in plan.referrers:
        print(f"  referrer 張替え: {rel}")
    if args.apply:
        rename.apply_rename(root, plan)
        print(f"  適用済み（referrer {len(plan.referrers)} 件＋git mv {len(plan.moves)} 対）")
    else:
        print(plan.diff() or "  （edge 変更なし・ファイル改名のみ）")
        print("\n（dry-run。書き込むには --apply を付けてください）")
    return EXIT_OK


def cmd_check_slug(args) -> int:
    """著作 slug（＋ ``--title`` を slugify した slug）がグローバル一意か fail-close 判定する。

    reconciliation-validator が書込前に Bash で呼ぶ決定論チェック（DD-22・Sub-D・issue #73）。
    衝突（既存コーパス id と一致 or 著作 slug 群内で重複）が 1 件でもあれば EXIT_ERROR。
    """
    root = _root(args)
    # 改変前の現状コーパスと照合するためディスク走査で index を作る（meta.json の陳腐化を避ける）。
    meta = build_meta(root)
    for nid, locs in duplicates(meta).items():
        print(f"警告: コーパスに既存 id 重複 {nid}（{', '.join(locs)}）。", file=sys.stderr)
    slugs = list(args.slugs)
    for d in getattr(args, "from_dir", []):
        base = Path(d)
        if not base.is_dir():
            print(f"エラー: --from-dir が存在しない: {d}", file=sys.stderr)
            return EXIT_NOT_FOUND
        found = sorted(p.stem for p in base.rglob("*.yaml"))
        if not found:
            print(f"警告: {d} 配下に *.yaml が無い", file=sys.stderr)
        else:
            print(f"--from-dir {d}: {len(found)} slug 収集（{', '.join(found)}）")
        slugs.extend(found)  # 重複はそのまま残す＝バッチ内重複を slug_collisions が検出
    if args.title:
        slugify = _load_slugify()
        for t in args.title:
            s = slugify(t)
            print(f"slugify: {t!r} → {s!r}")
            slugs.append(s)
    if not slugs:
        print("エラー: 判定する slug/title/--from-dir が無い", file=sys.stderr)
        return EXIT_NOT_FOUND
    collisions = query.slug_collisions(meta, slugs)
    if not collisions:
        print(f"OK: {len(slugs)} slug すべて一意（衝突なし）: {', '.join(slugs)}")
        return EXIT_OK
    print("NG: slug 衝突（グローバル一意違反・fail-close）", file=sys.stderr)
    for s, why in sorted(collisions.items()):
        print(f"  衝突 {s!r} … {why}", file=sys.stderr)
    return EXIT_ERROR


def cmd_build_view(args) -> int:
    root = _root(args)
    meta = load_meta(root, _meta_path(args, root))
    for nid, locs in duplicates(meta).items():
        print(f"警告: id 重複 {nid}（{', '.join(locs)}）。先勝ちを採用。", file=sys.stderr)
    out = Path(args.out).resolve() if args.out else root / viewer.DEFAULT_OUT
    model = viewer.build_view(root, meta, out)
    size = out.stat().st_size
    print(f"{len(model['nodes'])} ノードを HTML 化 → {out}（{size:,} bytes）")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=DEFAULT_ROOT,
                        help=f"v2 コーパス root（既定 {DEFAULT_ROOT}）")
    common.add_argument("--meta", help="meta.json のパス（既定 <root>/meta.json・無ければ走査）")

    parser = argparse.ArgumentParser(prog="dsv2", parents=[common],
                                     description="doc-system v2 ツール（索引・照会・辺逆転・改題）")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("index", parents=[common], help="meta.json を生成")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("deps", parents=[common], help="出辺（依存先）を表示")
    p.add_argument("id")
    p.set_defaults(func=cmd_deps)

    p = sub.add_parser("dependents", parents=[common], help="入辺（依存元）を表示")
    p.add_argument("id")
    p.set_defaults(func=cmd_dependents)

    p = sub.add_parser("orphans", parents=[common], help="完全孤立ノードを列挙")
    p.set_defaults(func=cmd_orphans)

    p = sub.add_parser("drift", parents=[common], help="ref_version ドリフト辺を列挙（RULE-004）")
    p.set_defaults(func=cmd_drift)

    p = sub.add_parser("reverse", parents=[common], help="FND 辺逆転（既定 dry-run）")
    p.add_argument("slug", help="FND の slug（=id）")
    p.add_argument("--apply", action="store_true", help="正本へ書込＋git mv（既定 dry-run）")
    p.set_defaults(func=cmd_reverse)

    p = sub.add_parser("rename", parents=[common], help="slug 改題（既定 dry-run）")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--apply", action="store_true", help="改名＋referrer 張替え（既定 dry-run）")
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser("check-slug", parents=[common],
                       help="著作 slug のグローバル一意 fail-close 判定（Sub-D・DD-22）")
    p.add_argument("slugs", nargs="*", help="判定する slug（＝ファイル名 stem）")
    p.add_argument("--title", action="append", default=[],
                   help="タイトルを slugify.py で slug 化して判定に加える（複数可）")
    p.add_argument("--from-dir", action="append", default=[], metavar="DIR",
                   help="ディレクトリ配下の *.yaml サイドカー stem を判定対象に収集（tmp ミラー走査・複数可）")
    p.set_defaults(func=cmd_check_slug)

    p = sub.add_parser("build-view", parents=[common],
                       help="meta.json ＋本文から単一 doc_view.html を生成")
    p.add_argument("--out", help="出力先 HTML（既定 <root>/doc_view.html）")
    p.set_defaults(func=cmd_build_view)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
