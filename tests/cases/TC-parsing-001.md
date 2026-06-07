---
id: TC-parsing-001
version: 1.0
---
# 自前フロントマター・パーサ＋lint（S5）

> 対象：`review_system.parsing`（[schema 対応文法](../../docs/schema/README.md)・[13 S5](../../docs/requirements/13-stabilization.md)・[DD7](../../docs/design/decisions.md)）。
> パーサ＝検証器。**対応サブセット外は実行前 fail-close**。境界値・エッジを厚く。

## 目的
mini-YAML サブセットを正しく読み、**範囲外記法を黙って通さず弾く**こと、lint が override/severity/determinism/必須キー/id 一意性/version MAJOR を検証することを確認する。

## 前提
Python 3.11・標準ライブラリのみ。`version` は `"MAJOR.MINOR"` 文字列で読む（整数化しない）。

## 手順
`python -m unittest -v tests.unit.test_parsing`

## 期待結果

### パーサ（対応サブセット）
| # | 入力 | 期待 |
|---|---|---|
| P1 | 正常フロントマター（マッピング＋`rules:` ブロック列） | dict に解釈・`rules` は list |
| P2 | スカラ型：`version: "1.0"`/`enabled: true`/`extends: null`/`severity: error` | str/bool/None/str に解釈 |
| P3 | 行コメント・行末コメント | 無視（値に混入しない） |
| P4 エッジ | 引用文字列内の `#`（`title: "a # b"`） | `#` を保持（コメント扱いしない） |
| P5 境界 | タブインデント | `MiniYamlError`（タブ禁止） |
| P6 境界 | フロースタイル `cats: [a, b]` | `MiniYamlError`（非対応） |
| P7 境界 | 複数行スカラ `desc: |` | `MiniYamlError` |
| P8 境界 | アンカー `&x` / エイリアス `*x` | `MiniYamlError` |
| P9 境界 | `.md` で閉じ `---` が無い | `MiniYamlError` |
| P10 エッジ | インデントが2の倍数でない（3 スペース） | `MiniYamlError` |

### lint（検証器・O-14 同形式）
| # | 入力 | 期待 |
|---|---|---|
| L1 | 妥当な基準（必須キー・override/severity 正常・id 一意・MAJOR 対応） | `ok`（エラー0件） |
| L2 | `override: loose`（不正値） | エラー（`override ∈ {locked,tighten-only,open}`） |
| L3 | `severity: fatal`（不正値） | エラー |
| L4 | `determinism: maybe`（不正値） | エラー |
| L5 | 必須キー `doc_type` 欠落 | エラー |
| L6 エッジ | `rules` の id 重複 | エラー（一意性違反・両 id を指摘） |
| L7 境界 | `version: "2.0"`（未対応 MAJOR） | エラー（fail-close） |
| L8 境界 | `version: "1.9"`（対応 MAJOR・新しい MINOR） | `ok`（MINOR は情報のみ） |
| L9 | `extends` 先が存在しない | エラー（継承リンク切れ） |
