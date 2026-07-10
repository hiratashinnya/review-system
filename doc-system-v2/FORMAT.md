# doc-system v2 フォーマット仕様（Sub-A・正本）

現行 doc-system（585 ノードが 23 の .md に同居・inline YAML＋`<details>` バッジ＋`---`/`## ` 境界の
自前パース）を刷新した新フォーマットの機械定義。関連 Issue: 傘 #76 / 本 Sub-A #70。

## 目的
- ① 本文とメタ属性の分離（機械検証と著作の簡素化）
- ② 連番 id 廃止（並行開発の競合抑止）
- ③ 1ノード1YAML（パーサ簡素化）＋本文は型別ポリシー

## 中核原則
> **path に載せるのは「単一値」ファセットだけ。多値・グラフ属性はサイドカー。**
- **単一値 → path**：stage / type / lifecycle status（該当型のみ）
- **多値・グラフ → サイドカー**：title / version / condition / labels / scheduled / edges（親子も edge）
- **id は path 非依存**（＝ファイル名 stem）。だから stage/status を `git mv` しても edge は壊れない。

## ファイル構成
```
doc_view.html          # Sub-F の生成器が meta.json + md から出力
config.yml             # stage/type/status 定義・必須辺ルール（型レベル）
meta.json              # 生成物（サイドカー集約・手編集しない）
slugify.py             # slug 正規化の唯一実装
schema/sidecar.schema.json
nodes/
  <stage>/<type>/[<status>/]{slug}.yaml    # サイドカー（属性・正本）
  <stage>/<type>/[<status>/]{slug}.md      # 本文（body_policy=required の同名本文）
  .../shared-body.md                       # 共有本文（body_policy=shared から body_ref.file で参照）
```

## 1ノード = 1 YAML、本文は型別 body policy
- `{slug}.yaml` … **ノード正本**。1 YAML に複数ノードを詰め込まない。`schema/sidecar.schema.json` に従う。
  - 持つ: `title` `version` `condition?` `labels` `scheduled`（非空） `edges[]` ＋ 正準 meta-schema フィールド
    `result?`/`log_ref?`（**TR 専用**・DD-011）・
    `carrier?`（設計要素の実現担体＝realization carrier。**#93 で enum 化**：`skill`/`agent`/`command`/`instructions`/`hooks`/`code`（値集合の SoT = `schema/sidecar.schema.json`）。v2 正準フィールド・オーナー承認済 2026-07-03）。
    `body_ref.file?`/`body_ref.anchor?`（共有 Markdown 本文への参照。`body_policy=shared` の型で使う）。
    `source.file?`/`source.qualname?`/`source.kind?`（**SRC 専用**。実装識別子の所在）。
    `test.file?`/`test.qualname?`/`test.kind?`（**TC 専用**。実テスト識別子の所在）。
    （`suppress?`/`suppress_reason?` は issue #118 で抑制機構ごと廃止済み・スキーマ非対応）
  - **持たない**: `id`（=stem）・`type`（=path 第2階層）・`status`（=path 第3階層）・`resolved`（=FND の path）＝二重管理回避。
- Markdown 本文 … 属性・バッジ・YAML は書かない。本文の要否は `config.yml: body_policy` で決まる。
  - `required`: 同名 `{slug}.md` が必須。
  - `shared`: `body_ref.file`（任意で `body_ref.anchor`）で共有 Markdown 本文を指せる。同名 `{slug}.md` も互換として許可。
  - `none`: Markdown 本文を要求しない。移行中の同名 `{slug}.md` は存在しても違反にしない。
  - 現行ポリシー: `td=shared`、`tc/src=none`、その他の既存型は `required`。

## id / slug（§slug）
- **id = ファイル名 stem = 正規化した読めるタイトル**。パス非依存・**グローバル一意**。
- 正規化は `slugify.py`（唯一実装）: ①末尾 condition マーカー除去 ②NFC ③backtick・path/shell 敵性文字除去
  ④空白→`-` ⑤ASCII 小文字化（日本語不変）⑥連続 `-` 単一化・前後 trim ⑦UTF-8 120 byte 上限。
- 例: `本文中の孤立 \`---\` を検出したとき WARNING を出力する（failure）`
  → `本文中の孤立-を検出したとき-warning-を出力する`
- **一意性はここでは保証しない**。reconciliation-validator が書込前に fail-close で担保（DD-22・Sub-D）。
- **改題**（title 変更で slug が変わる）は稀。変わる場合は `rename` ツール（Sub-C）が全 referrer の
  `to:` を meta.json 経由で機械一括張替え。

## path 規約
`nodes/<stage>/<type>/[<status>/]{slug}.yaml`（本文は body policy に従う）
- stage / type の対応は `config.yml: layout`（stage ディレクトリ → type 群）が唯一の機械可読ソース。
  requirements stage は 01-why(val/sr) と 02-what(fr/nfr/spec) の2ディレクトリに分かれる。
- stage: `01-why | 02-what | 03-analysis | 05-design | 04-verification`
- implementation stage の SRC は `06-implementation/src/{slug}.yaml` に置く。SRC は `body_policy=none` で
  Markdown 本文を要求せず、`source.file` + `source.qualname` + `source.kind` を正本にして実装識別子を指す。
- type: `config.yml: layout` の各値（val, sr, …, fnd, dd, q, pend）。**type は path から導出**。
- status（lifecycle 型のみ・**path から導出**）:
  - `fnd`: `open | resolved`
  - `q`: `open | decided | deferred | closed`
  - `dd`: `decided | closed`
  - `pend`: `open | resolved | deferred`
  - 他の型は status ディレクトリを取らない。

## edges（無名依存辺・親子も edge）
サイドカー `edges[]` の各要素:
- `to`（必須）: 参照先の **slug**（path 非依存）。
- `ref_version`（任意）: 参照時点の相手 `x.y`。相手バッジ `x.y.z` の `x.y` と不一致でドリフト（RULE-004）。
- `note`（任意）: 補足。

**edge は無名**（現行 doc-system の「無名依存辺」を踏襲・`kind` を持たない）。関係の意味は
**(source 型, target 型) ＋ `config.yml: required_edges` ＋ FND resolved 状態から導出**する:
- 親子（umbrella→子）＝ 同型間の依存辺（例: `SPEC→SPEC` は refines＝親）。
- 入出力・詳細化＝ 型ペアで一意（例: `O→P`・`O→ACTOR`・`MOD→P/D` は target 型で判別）。
- backref＝ `node→FND`（FND resolved）の向きで判別（逆転時に付与・指摘時 ref_version は FND 本文に記録＝DD-3）。
- TD-TC は `config.yml: exact_link_counts` で 1:1 を表す。TD はちょうど1つの TC から実装され、TC は
  ちょうど1つの TD を実装する。

## condition（テスタブルなアサーションの条件区分）
- 語彙は現行 `config.yml: condition_vocab` を踏襲: **`normal | boundary | empty | failure | error`**（新設・削除なし）。
  - normal=正常系 / boundary=境界値 / empty=空・ゼロ件・null / failure=仕様違反を正しく検出（sad-path）/ error=処理不能な異常入力（fail-close 対象）。
- **非テスタブル**（傘・トレーサビリティ用）ノードは `condition` を**省略**する。
- **傘（umbrella）は condition 値ではない**。傘性は「同型の子から被参照される」構造から導出する（condition に umbrella を混ぜない＝子を代表せずミスリードになるため）。同型 child→parent 辺の target になっている傘 SPEC は RULE-016 対象外で、condition を持たない。
- **always_error は condition とは別軸**。RULE-005/007 のような抑制不可性は config の `always_error` で表し、condition は入力等価クラス（failure/error 等）で割り当てる。

## 版（DD-8 踏襲）
- `version` は `MAJOR.MINOR.PATCH`。MAJOR=構造/型、MINOR=内容、PATCH(z)=format/provenance/lifecycle。
- RULE-004 は `x.y` を比較（z は伝播不問）。backref/provenance/辺逆転は z バンプ。

## status 遷移（git mv）
- 例: FND を解決 → `nodes/.../fnd/open/{slug}.*` を `nodes/.../fnd/resolved/{slug}.*` へ `git mv`。
- **id（slug）不変ゆえ参照は壊れない**。遷移は reconciliation が edge 逆転（`backref`）＋`git mv`＋z バンプ
  として機械実行（手作業でない）。git rename 履歴で監査可能（PR8「消さない」と整合）。

## meta.json（生成物）
- `nodes/**` を走査し、path から stage/type/status を、`{slug}.yaml` から残りを集約した単一 index。
- `body_policy`、解決済み `body_path`、`body_anchor` も集約する。bodyless ノードの `body_path` は `null`。
- グラフ照会（deps/dependents/孤立/ドリフト）と viewer（Sub-F）が消費。**手編集しない**（再生成で最新化）。
- 人間のブラウズ/検索は `ls`/`find`/`grep`（index/search ツールは不要化）。

## 検証（Sub-A で提供）
- `slugify.py`（自己テスト付き）・`validate.py`（stdlib のみ・`docidx/nodeyaml.py` 流用）。
- `validate.py` は schema（必須キー/型/enum/pattern・未知キー禁止）＋path（stage/type/status 既知集合）
  ＋body policy（required/shared/none）＋id 一貫性（stem == slugify(title)）を検査。**edge.to の存在確認・一意性は範囲外**（前者=meta.json/Sub-C、後者=Sub-D）。
- サンプル: `nodes/02-what/spec/`（umbrella＋子・親子 edge）・`nodes/04-verification/fnd/open/`（status＝path）。

## 非スコープ（後続サブ）
- 585 ノードの移行 = Sub-B #71 / ツール刷新 = Sub-C #72 / 著作パイプライン = Sub-D #73 /
  テンプレ・config・notation 正式化 = Sub-E #74 / viewer 生成器 = Sub-F #75。
