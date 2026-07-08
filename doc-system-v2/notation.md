# ノード＆エッジ記法（doc-system v2）

> doc-system v2 の著作記法。**1ファイル1ノード＝本文 `.md` ＋サイドカー `.yaml` のペア**。
> 機械定義の正本は [FORMAT.md](FORMAT.md)・[config.yml](config.yml)・[schema/sidecar.schema.json](schema/sidecar.schema.json)、
> テンプレは [templates/](templates/)。本書はそれらを著作者向けにまとめた記法ガイド。
> 旧 `docs/doc-system/04-notation.md`（`<details>` バッジ＋inline YAML）を置換する。

## 1. 1ノード = 2ファイル

各ノードは同名 stem の 2 ファイルで表す。**属性・バッジ・YAML を本文に混ぜない**。

```
nodes/<stage>/<type>/[<status>/]{slug}.md      # 本文のみ（Markdown）
nodes/<stage>/<type>/[<status>/]{slug}.yaml    # サイドカー（属性・辺）
```

- `.md` … 本文のみ。前提条件・期待動作・論点などの人間向け記述。**YAML ブロックも `<details>` バッジも書かない。**
- `.yaml` … サイドカー。`schema/sidecar.schema.json` に従い、`title` `version` `condition?` `labels` `scheduled` `edges[]` を持つ。

> **持たないもの**: `id`（＝ファイル名 stem）／`type`（＝path 第2階層）／`status`（＝path 第3階層）。
> path とサイドカーの二重管理を避けるため、これらはサイドカーに書かない。

## 2. id / slug

- **id = ファイル名 stem = 正規化した読めるタイトル**。path 非依存・グローバル一意。
- 正規化は [`slugify.py`](slugify.py)（唯一実装）: ①末尾 condition マーカー除去 ②NFC ③backtick・path/shell 敵性文字除去 ④空白→`-` ⑤ASCII 小文字化（日本語は不変）⑥連続 `-` 単一化・前後 trim ⑦UTF-8 120 byte 上限。
- 例: `本文中の孤立 \`---\` を検出したとき WARNING を出力する` → `本文中の孤立-を検出したとき-warning-を出力する`
- **一意性はここでは保証しない**。書込前に reconciliation-validator が fail-close で担保（DD-22・Sub-D）。
- **改題**（title 変更で slug が変わる）は稀。変わる場合は `rename` ツール（Sub-C）が全 referrer の `to:` を meta.json 経由で機械一括張替え。

## 3. path 規約（stage / type / status を表す）

`nodes/<stage>/<type>/[<status>/]{slug}.{md,yaml}`

- **stage / type の対応は [`config.yml: layout`](config.yml) が唯一の機械可読ソース**。type は path 第2階層から導出する。
- stage: `01-why | 02-what | 03-analysis | 05-design | 04-verification`。
  - requirements stage は `01-why`（VAL/SR）と `02-what`（FR/NFR/SPEC）の2ディレクトリに分かれる。
- status（**lifecycle 型のみ**・path 第3階層から導出）:
  - `fnd`: `open | resolved`
  - `q`: `open | decided | deferred | closed`
  - `dd`: `decided | closed`
  - `pend`: `open | resolved | deferred`
  - 他の型は status ディレクトリを取らない。
- **status 遷移は `git mv`**（例: FND 解決 → `.../fnd/open/{slug}.*` を `.../fnd/resolved/{slug}.*` へ）。id（slug）不変ゆえ参照は壊れない。遷移は reconciliation が edge 逆転（`backref`）＋`git mv`＋z バンプとして機械実行する（手作業でない）。

## 4. サイドカー属性

```yaml
title: "本文中の孤立 `---` を検出したとき WARNING を出力する"  # 必須。記号・backtick 可。slug の元。
version: "0.1.1"        # 必須。MAJOR.MINOR.PATCH（DD-8）。ドリフト判定は x.y、z は伝播不問。
condition: failure      # テスタブルなアサーションのみ。傘/非テスタブルは省略。
labels: []              # 多値ラベル（post-mvp 等）。多値ゆえ path 化不可。
scheduled: "sprint-1"   # 実施スプリント。既定=current_phase（config.yaml）。空=オーナー承認済みの後送り/未計画のみ。繰り越しはオーナー判断。
edges: []               # 無名依存辺（§5）。空でもキーは必須。
```

- **condition**（`config.yml: condition_vocab`）: `normal | boundary | empty | failure | error`。
  - normal=正常系 / boundary=境界値 / empty=空・ゼロ件・null / failure=仕様違反を正しく検出（sad-path）/ error=処理不能な異常入力（fail-close 対象）。
  - **非テスタブル（傘・トレーサビリティ用）ノードは `condition` を省略**する。傘性は「同型の子から被参照される」構造から導出する（condition に `umbrella` を混ぜない）。同型 child→parent 辺の target になっている傘 SPEC は RULE-016 対象外。
  - **always_error は condition とは別軸**。抑制不可性は config の `always_error` で表し、condition は入力等価クラスで割り当てる。
- **version**: MAJOR=構造/型、MINOR=内容、PATCH(z)=format/provenance/lifecycle。RULE-004 は `x.y` を比較。

## 5. edges（無名依存辺・親子も edge）

`edges[]` の各要素は無名の有向辺（`kind` を持たない）。

```yaml
edges:
  - to: "ノード本文に孤立-ノード分離記法の本文内誤用-が存在しない"   # 必須: 参照先の slug（path 非依存）
    ref_version: "0.1"                                              # 任意: 参照時点の相手 x.y
    note: "補足があれば"                                            # 任意
```

- **`to` は slug スカラーのみ**。複数依存は**辺を分割**する（リスト記法は禁止）。
- **`ref_version`** は相手バッジ `x.y.z` の `x.y` と不一致でドリフト（RULE-004）。z は伝播不問。
- **`kind` / `status` は書かない**。関係の意味は **(source 型, target 型) ＋ `config.yml: required_edges` ＋ FND resolved 状態** から導出する:
  - 親子（umbrella→子）＝ 同型間の依存辺（例 `SPEC→SPEC` は refines＝親）。
  - 入出力・詳細化＝ 型ペアで一意（例 `O→P`・`O→ACTOR`・`P→I`・`MOD→P/D`）。
  - backref＝ `node→FND`（FND resolved）の向きで判別（逆転時に付与・指摘時 ref_version は FND 本文に記録＝DD-3）。
- **義務辺（決定スパイン）**: `DD→X`・`Q→X`・`PEND→X` は**辺の存在＝未反映**。反映完了で辺を削除し、対象側に `X→DD` を張る（RULE-001/002/022）。

## 6. 本文（`.md`）の書き方

本文は Markdown のみ。テンプレ（[templates/](templates/)）の項目見出しを埋める。

- SPEC/TD: **前提条件 / 入力・トリガ / 期待動作**（TD はテスト観点 / 前提 / 入力 / 期待結果）。
- E: **スティミュラス / アクション / レスポンス / アフェクト**。
- DD/Q: **論点 / 選択肢 / 決定（推奨）/ 影響範囲（ブロッカー）**。
- FND: **指摘 / 深刻度 / 推奨 / 指摘時 ref_version**（DD-3）。

> **`---`（水平線）を本文に書かない**。旧記法ではノード分離に使ったが、v2 は 1 ファイル 1 ノードのため分離は不要で、
> 本文中の孤立 `---` はパーサ由来の silent 截断リスクとなる（サンプル SPEC 参照）。

## 7. meta.json（生成物・手編集しない）

- `nodes/**` を走査し、path から stage/type/status を、`{slug}.yaml` から残りを集約した単一 index。
- グラフ照会（deps/dependents/孤立/ドリフト）と viewer（Sub-F）が消費する。**再生成で最新化**する。
- 人間のブラウズ/検索は `ls`/`find`/`grep`（旧 index/search ツールは不要化）。

## 8. 検証

- [`validate.py`](validate.py)（stdlib のみ）が schema（必須キー/型/enum/pattern・未知キー禁止）＋ path（stage/type/status 既知集合）＋ id 一貫性（stem == slugify(title)）を検査する。
- **存在確認・グローバル一意は範囲外**（前者＝meta.json/Sub-C、後者＝reconciliation-validator/Sub-D）。

## 9. 旧記法（v1）→ 新記法（v2）対応表

| 旧（`docs/doc-system/`・v1） | 新（`doc-system-v2/`・v2） |
|---|---|
| 1 ファイルに複数ノード（`##` 見出し＋`---` 区切り） | **1 ファイル 1 ノード**（md＋yaml のペア）。区切り `---` は廃止 |
| `<details><summary>⬡ ID · vX.Y.Z</summary>` バッジ | 廃止。version はサイドカー `version`、id はファイル名 stem |
| 本文中の inline `yaml` ブロック | サイドカー `{slug}.yaml` に分離 |
| `id: PREFIX-N`（連番 ID） | **id = slug（正規化タイトル）**。連番廃止（並行開発の競合抑止） |
| `type: FR` フィールド | path 第2階層 `<type>` から導出（サイドカーに持たない） |
| 本文中の `**status: open**` 等 | path 第3階層 `<status>` から導出（fnd/q/dd/pend・`git mv` で遷移） |
| `edges[].to: SR-001`（ID 参照） | `edges[].to: "<slug>"`（slug 参照・path 非依存） |
| `kind` / `status`（辺）… 既に v1 で廃止済み | 引き続き無し（無名依存辺） |
| `suppress: [RULE-xxx]`（理由は本文/コメント） | **#81 で正式化 → #118 でスキーマごと廃止**（抑制機構自体を撤去・drift は無条件発火。旧 `suppress`/`suppress_reason` フィールドは非対応） |
| TR `result` / `log_ref`（YAML メタ） | **#81 で正式化**：サイドカーの機械可読フィールド（RULE-020/021・DD-011） |
| （新）`carrier`（設計要素の実現担体） | **#81 で正式化**：サイドカー `carrier`。**#93 で enum 化**：`skill`/`agent`/`command`/`instructions`/`hooks`/`code` |

## 10. schema 差分は #81 で解決済み

旧テンプレが「v2 サイドカー schema 未対応」として打ち上げていた属性は、**PR #81（オーナー承認 2026-07-03）で正準フィールドとして schema に追加**され決着した:

- **TR の `result`（PASS|FAIL）/ `log_ref`**（RULE-020/021 の機械検査対象・DD-011 で body→メタ昇格）。
- **`carrier`**（設計要素の実現担体）。**#93 で enum 化**：`skill`/`agent`/`command`/`instructions`/`hooks`/`code`（値集合の SoT = `schema/sidecar.schema.json`）。

（旧 **`suppress`（配列）/ `suppress_reason`** は #81 で正式化されたが、**#118 で抑制機構自体を撤去**しスキーマから除去済み。依存先ノード更新時の影響確認を必須化し、drift（RULE-004）は凍結せず常に発火させる方針に一本化。）

現行サイドカー schema（`additionalProperties: false`）の**許可トップレベルキー**は:
`title / version / condition / labels / scheduled / result / log_ref / carrier / edges`。
