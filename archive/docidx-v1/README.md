# docidx-v1 — doc-system v1-legacy ノード検索/読み込みツール（archive）

> **archive 済み（issue #172）**：本パッケージは `docidx/`（リポジトリ直下）から
> `archive/docidx-v1/` へ `git mv` された（消さない＝PR8、`python -m docidx` を v2 作業で
> 誤って使ってしまうミスの温床を構造的に断つため）。
>
> **v1/v2 スコープの注意（issue #76・v1→v2 cutover 後）**：
> `scan.py`・`cli.py`・`query.py`・`render.py`・`model.py` は **v1-legacy 専用**。旧インライン YAML
> 埋め込みフォーマット（`<details><summary>⬡ <ID> · vX.Y.Z</summary>` パース規約）を読み、対象は
> `doc-system-v1-archive/`（旧 `doc-system/` を archive 化・`git mv`・issue #76）。**現行コーパスは
> `doc-system-v2/`（1ノード=`{slug}.md`＋`{slug}.yaml` の対）で、これは本パッケージの対象外**——
> v2 の索引・照会は `python3 -m dsv2`（`dsv2/`）を使う。
> 委譲先の `dsv2-lookup`（旧名 `docidx-lookup`・issue #173 で改名）サブエージェントは dsv2-native に
> 書き換え済み（`.claude/agents/dsv2-lookup.md`）。

## archive 判断の経緯（issue #142 → issue #172）

- issue #142（2026-07-10 時点）: 「`docidx/` は物理 archive へ移動しない」と判断した。理由は
  `nodeyaml.py`（YAML ブロックリーダ）を v2 の `dsv2/meta.py`・`doc-system-v2/validate.py` が
  現役 import しており、`docidx/` ごと `archive/` へ移すと v2 実行系を壊すため。
- issue #172: `nodeyaml.py`（`re`/`typing` のみに依存する完全自己完結モジュール・参照元は
  `dsv2/meta.py`・`doc-system-v2/validate.py` の2箇所のみ）だけを **`dsv2/nodeyaml.py`** へ
  切り出し、残り（`scan.py`/`cli.py`/`query.py`/`render.py`/`model.py`/`__init__.py`/`__main__.py`）
  を本ディレクトリへ `git mv` した。これで v1-legacy 専用ツールと v2 共有インフラが物理的に分離され、
  誤起動リスクが下がった。
- `scan.py` は `nodeyaml.parse` を使うため、本パッケージから `dsv2.nodeyaml` を import する
  （legacy → 現行 v2 という依存方向になる点に注意。`dsv2/README.md` にも記載）。

[md2idx](https://github.com/oubakiou/md2idx) と同じ思想（**コンテキスト効率**）の read-only ユーティリティ。
巨大な `doc-system/`（現 `doc-system-v1-archive/`）の Markdown 全体を読み込む代わりに、軽量なインデックス
（目次）を作り、必要なノードだけをオンデマンドで読み込む。標準ライブラリのみ。

## 使い方

ディレクトリ名にハイフンを含む（`docidx-v1`）ため `import docidx-v1` の構文は書けないが、
`python -m` はモジュール名を文字列として解決するためハイフンを含んでいても動作する。
リポジトリ root から実行する（`archive/` は暗黙 namespace package として解決される）。

```bash
python3 -m archive.docidx-v1 index                  # 全ノードの目次（JSON）
python3 -m archive.docidx-v1 index --format table    # 人間向けテーブル
python3 -m archive.docidx-v1 search --type FND --text ドリフト   # 型＋キーワード検索
python3 -m archive.docidx-v1 search --id 'SPEC-1-*'              # ID グロブ
python3 -m archive.docidx-v1 show FR-1 SPEC-1-1      # ノード全体（yaml＋本文）を読み込む
python3 -m archive.docidx-v1 deps SPEC-1-1           # 依存先（出辺）＋ドリフト判定
python3 -m archive.docidx-v1 dependents FR-1         # 依存元（入辺・逆引き）
```

- `--format json|table`（既定 `json`、サブコマンドの前後どちらでも指定可）
- `--root` でリポジトリ root を明示（既定: `doc-system/` を上方向に自動検出。現行リポジトリでは
  実ディレクトリ名が `doc-system-v1-archive/` のため自動検出に頼らずリポジトリ root から無指定で
  実行するか、`--root` を明示すること）
- `--config` で `config.yaml` のパスを明示（既定: `<root>/docs/doc-system/config.yaml` の `trace_scope`）
- 終了コード: `0` 正常 / `2` 未検出 / `3` 用法 / `4` config（`trace_scope` を解釈できない）

> 補足: `doc-system-v1-archive/`（実ノードのツリー）と `docs/doc-system/`（メタ仕様＝notation/meta-schema/
> config.yaml）は別物。`--root` は前者で root を決め、既定の `--config` は後者の `config.yaml` を読む。

## trace_scope（in-graph 範囲）の読み取り

走査対象は `config.yaml` の `trace_scope` が唯一の真実源。本ツールは**インラインリスト形式のみ**対応する。

```yaml
trace_scope:
  include: ["doc-system-v1-archive/**/*.md"]  # ✅ 対応（インラインフロー）
  exclude: ["docs/**", "**/README.md"]        # ✅（省略時は空集合）
```

ブロック形式（`- item`）・`trace_scope` ブロック欠如・config 欠如・`include` 欠如は**読めない**ものとして
扱い、**既定値へ黙ってフォールバックせず警告を出して停止する**（終了コード `4`）。ハードコード既定値で
すり替えると config 変更（ブロック化・グロブ追加）が本ツールに効かないドリフトを生むため。
警告文はインラインリスト形式のみ対応である旨を案内するので、`config.yaml` の記法を直すこと。

```yaml
trace_scope:
  include:
    - doc-system-v1-archive/**/*.md   # ❌ ブロック形式は未対応 → エラーで停止（コード4）
```

## ノード ID 重複の扱い

ID が重複した場合、索引は**先勝ち**（最初の出現を保持）で解決するが、**重複を検知したら stderr に
警告**を出す（どの ID が・どの `file:line` 群で重複し・どれを採用したかを明示）。read-only な情報
ツールとして処理自体は継続する（重複は doc-system 側のデータ不整合で、是正は検証ツールの責務）。

## パース規約

`docs/doc-system/04-notation.md §8` に従う。`<details><summary>⬡ <ID> · vX.Y.Z</summary>` 行の
次の ```yaml``` ブロックをノードとして読み、見出しは直前の `## ` 行、本文は `</details>` 以降
〜次の境界（`## ` / `---` / 次ノード）まで。本文中の例（インラインの `⬡ ...` や ```yaml```）は
`<summary>` タグの有無で誤検出しない。パース不能ブロックは全体を止めず当該ノードに
`parse_error` を記録する（fail-soft）。

## フォーマット依存マップ（関数単位）

本パッケージは doc-system の Markdown フォーマット仕様に依存する。仕様（SPEC ノード／notation 文書）が
改版されたら、下表と各関数 docstring の `依存仕様:` 行を見直すこと（版は凍結参照）。

| 関数 / 型 | 依存ポイント | 依存仕様（id・版／節） |
|---|---|---|
| `scan._is_node_summary_line` / `_parse_summary` | summary バッジでノード発見・版取得・例の誤検出回避 | SPEC-1-1 v0.1・SPEC-1 v0.3・04-notation §8・02-meta-schema §1 (DD-8 v0.1.1) |
| `scan.parse_markdown` | ノード発見と構造化／見出し=直前 `## `・本文=`</details>` 後／マーカー直後 YAML 欠如 | SPEC-1 v0.3・SPEC-1-1 v0.1・SPEC-1-2 v0.1・04-notation §4,§8 |
| `scan._make_node` | id/type/labels/scheduled/edges の抽出 | SPEC-1-1 v0.1 |
| `scan.load_trace_scope` / `discover_files` / `build_index` | trace_scope の include/exclude で in-graph 判定（空集合含む） | SPEC-24 v0.2・SPEC-31 v0.1・config.yaml: trace_scope |
| `model.Edge` | edge スキーマ（`to`/`ref_version`/`note`・`kind`/`status` なし） | SPEC-1-1 v0.1.1・04-notation §3（補助） |
| `model.Node`（`version`） | 版の真実源は summary バッジ x.y | 02-meta-schema §1 (DD-8 v0.1.1) |
| `query._drift` / `deps` / `dependents` | ドリフト＝辺 `ref_version` と参照先バッジ x.y の比較（情報提示のみ） | SPEC-9 v0.2・02-meta-schema §1 (DD-8 v0.1.1) |

> `nodeyaml.parse` / `_parse_edges`（YAML ブロック文法・edge スキーマ）は issue #172 で
> `dsv2/nodeyaml.py` へ分離済み。フォーマット依存マップは `dsv2/README.md` を参照。

> ドリフトは**情報提示のみ**。FND 起票・RULE 発火（検証）は doc-system 検証ツール側の責務で、
> 本パッケージは行わない（PR2: 機械取得と運用判定を混ぜない）。

## スコープ外（v1）

グラフ全体の検証（RULE-001…029）、ノードの書き込み/変更、`.idx` キャッシュの永続化、
あいまい/意味検索。ドリフトは `deps`/`dependents` の辺ごとフラグとしてのみ提示する。
