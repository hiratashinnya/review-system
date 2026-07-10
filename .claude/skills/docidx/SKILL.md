---
name: docidx
description: Retrieve/load specific doc-system nodes (by id/type/label/keyword) without reading whole files, via the docidx Python CLI (`python3 -m archive.docidx-v1` — index/search/show/deps/dependents). Use BEFORE opening a large doc-system/*.md to find a node — build a lightweight index, then load only the nodes you need (md2idx philosophy). Read-only. Not validation (no coverage/gap/value-path checks — see spec-inspector/value-trace), not node authoring (see the *-author agents).
---

# docidx — ノード検索/読み込み（md2idx 思想）

> **フォーマットの対象（v1／v2）**：`docidx`（`python3 -m archive.docidx-v1`）は **v1 コーパス `doc-system/`**（巨大 Markdown にノードが埋め込まれた旧フォーマット）専用。
> **doc-system v2（`doc-system-v2/nodes/**` ＝ 1ノード=`{slug}.md`＋`{slug}.yaml` の対・issue #73/#76）の照会は `dsv2` CLI（`python3 -m dsv2` — index/deps/dependents/orphans/drift/check-slug）を使う**。
> v2 では 1 ノード = 2 ファイルで巨大ファイル埋め込みが無いため、ブラウズは `ls`/`find`/`grep` でも代替でき、グラフ照会は `dsv2` が担う。v1/v2 併存期はどちらのコーパスを見ているかで使い分ける。
> issue #172 で実体を `docidx/` から `archive/docidx-v1/` へ退避（共有 YAML リーダ `nodeyaml.py` は `dsv2/nodeyaml.py` へ分離）。

doc-system のノードは巨大な Markdown（例: `02-what/03-spec.md` 4,900+ 行）に埋め込まれている。
1 ノードを見たいだけでファイル全体をコンテキストへ読み込むのは無駄。**まず軽量インデックスを作り、
必要なノードだけをオンデマンドで読み込む**のが docidx（実体＝`archive/docidx-v1/`・`python3 -m archive.docidx-v1`）。

委譲したいとき（探索ループを別コンテキストに逃がしてダイジェストだけ受け取る）は
サブエージェント **`dsv2-lookup`**（旧名 `docidx-lookup`・issue #173 で v2-native であることが分かる名前へ改名）を使う。フォーマット依存の詳細は `archive/docidx-v1/README.md` の
「フォーマット依存マップ」を参照。

## いつ使うか
- doc-system のノードを ID／型／ラベル／キーワードで探したい。
- あるノードの本文だけを読みたい（ファイル全体は不要）。
- あるノードの依存先（出辺）・依存元（入辺・逆引き）を辿りたい。
- **巨大ファイルを Read で開く前に**まず docidx で当たりを付ける。

## 使い方
```bash
python3 -m archive.docidx-v1 index                       # 全ノードの目次（既定 JSON）
python3 -m archive.docidx-v1 index --format table | head # 人間向けテーブル
python3 -m archive.docidx-v1 search --type FND --text ドリフト   # 型＋キーワード
python3 -m archive.docidx-v1 search --id 'SPEC-1-*'              # ID グロブ
python3 -m archive.docidx-v1 show FR-1 SPEC-1-1          # ノード全体（yaml＋本文＋file:line）
python3 -m archive.docidx-v1 deps SPEC-1-1               # 依存先（出辺）＋ドリフト
python3 -m archive.docidx-v1 dependents FR-1             # 依存元（入辺・逆引き）
```
(リポジトリ root から実行する。`archive/` は暗黙 namespace package として解決される。)
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
