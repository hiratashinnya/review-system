---
name: docidx
description: Retrieve/load specific doc-system nodes (by id/type/label/keyword) without reading whole files, via the docidx Python CLI (`python -m docidx` — index/search/show/deps/dependents). Use BEFORE opening a large doc-system/*.md to find a node — build a lightweight index, then load only the nodes you need (md2idx philosophy). Read-only. Not validation (no coverage/gap/value-path checks — see spec-inspector/value-trace), not node authoring (see the *-author agents).
---

# docidx — ノード検索/読み込み（md2idx 思想）

doc-system のノードは巨大な Markdown（例: `02-what/03-spec.md` 4,900+ 行）に埋め込まれている。
1 ノードを見たいだけでファイル全体をコンテキストへ読み込むのは無駄。**まず軽量インデックスを作り、
必要なノードだけをオンデマンドで読み込む**のが docidx（実体＝`docidx/`・`python -m docidx`）。

委譲したいとき（探索ループを別コンテキストに逃がしてダイジェストだけ受け取る）は
サブエージェント **`docidx-lookup`** を使う。フォーマット依存の詳細は `docidx/README.md` の
「フォーマット依存マップ」を参照。

## いつ使うか
- doc-system のノードを ID／型／ラベル／キーワードで探したい。
- あるノードの本文だけを読みたい（ファイル全体は不要）。
- あるノードの依存先（出辺）・依存元（入辺・逆引き）を辿りたい。
- **巨大ファイルを Read で開く前に**まず docidx で当たりを付ける。

## 使い方
```bash
python -m docidx index                       # 全ノードの目次（既定 JSON）
python -m docidx index --format table | head # 人間向けテーブル
python -m docidx search --type FND --text ドリフト   # 型＋キーワード
python -m docidx search --id 'SPEC-1-*'              # ID グロブ
python -m docidx show FR-1 SPEC-1-1          # ノード全体（yaml＋本文＋file:line）
python -m docidx deps SPEC-1-1               # 依存先（出辺）＋ドリフト
python -m docidx dependents FR-1             # 依存元（入辺・逆引き）
```
- `--format json|table`（既定 `json`、サブコマンドの前後どちらでも指定可）。
- `--root` でリポジトリ root、`--config` で config.yaml を明示（既定は自動検出）。
- 終了コード: `0` 正常 / `2` 未検出 / `3` 用法 / `4` config（`trace_scope` を解釈できない）。
- `trace_scope` は**インラインリスト形式のみ**対応（ブロック形式・config 欠如は既定にフォールバックせず停止）。ID 重複は先勝ち＋stderr 警告。

## 注意（責務の境界）
- **read-only**。ノードの編集・起票はしない（著作は `*-author`→`reconciliation`）。
- `deps`/`dependents` の **drift は情報提示のみ**。FND 起票・RULE 判定（検証）は行わない（PR2）。
- 仕様点検（カバレッジ/穴/価値経路）は守備範囲外＝`spec-inspector`・`/value-trace` を使う。

## done 条件
- [ ] 目的のノードを `show`/`search` で取得し、ファイル全体の Read を回避できた。
- [ ] 辺を辿る必要があれば `deps`/`dependents` で取得した。
