# docidx — doc-system ノード検索/読み込みツール

[md2idx](https://github.com/oubakiou/md2idx) と同じ思想（**コンテキスト効率**）の read-only ユーティリティ。
巨大な `doc-system/` の Markdown 全体を読み込む代わりに、軽量なインデックス（目次）を作り、
必要なノードだけをオンデマンドで読み込む。標準ライブラリのみ。

## 使い方

```bash
python -m docidx index                  # 全ノードの目次（JSON）
python -m docidx index --format table   # 人間向けテーブル
python -m docidx search --type FND --text ドリフト   # 型＋キーワード検索
python -m docidx search --id 'SPEC-1-*'              # ID グロブ
python -m docidx show FR-1 SPEC-1-1     # ノード全体（yaml＋本文）を読み込む
python -m docidx deps SPEC-1-1          # 依存先（出辺）＋ドリフト判定
python -m docidx dependents FR-1        # 依存元（入辺・逆引き）
```

- `--format json|table`（既定 `json`、サブコマンドの前後どちらでも指定可）
- `--root` でリポジトリ root を明示（既定: `doc-system/` を上方向に自動検出）
- `--config` で `config.yaml` のパスを明示（既定: `<root>/docs/doc-system/config.yaml` の `trace_scope`）
- 終了コード: `0` 正常 / `2` 未検出 / `3` 用法

## パース規約

`docs/doc-system/04-notation.md §8` に従う。`<details><summary>⬡ <ID> · vX.Y</summary>` 行の
次の ```yaml``` ブロックをノードとして読み、見出しは直前の `## ` 行、本文は `</details>` 以降
〜次の境界（`## ` / `---` / 次ノード）まで。本文中の例（インラインの `⬡ ...` や ```yaml```）は
`<summary>` タグの有無で誤検出しない。パース不能ブロックは全体を止めず当該ノードに
`parse_error` を記録する（fail-soft）。

## スコープ外（v1）

グラフ全体の検証（RULE-001…029）、ノードの書き込み/変更、`.idx` キャッシュの永続化、
あいまい/意味検索。ドリフトは `deps`/`dependents` の辺ごとフラグとしてのみ提示する。
