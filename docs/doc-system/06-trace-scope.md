---
version: "0.1.0"
---
# トレース対象集合

> 検証ツールが走査するドキュメントの集合（in-graph の確定）。
> **C3**：この集合は検証器実装着手前に確定が必須（README §C3）。
> 検証ルールの定義は [02 §9](02-meta-schema.md)、検証戦略は [05](05-verification.md)。

---

## 1. 基本方針

**in-graph**（検証対象）とするドキュメントの判断基準：

1. **ノード ID を持つ**：`<details><summary>⬡ PREFIX-N` の形式を含む
2. **上流参照辺を持つ**：`edges:` ブロックで他ノードを参照する
3. **RULE の適用対象**：型・辺・ステータスに対してルールが発火する

上記のいずれかを満たすファイルは in-graph として扱う。

---

## 2. トレース対象ファイル一覧（in-graph）

| ファイルパス | 含む型 | 備考 |
|---|---|---|
| `docs/requirements/why/val.md` | VAL | 価値命題（根ノード） |
| `docs/requirements/why/sr.md` | SR | ステークホルダー要求 |
| `docs/requirements/what/fr.md` | FR | 機能要求 |
| `docs/requirements/what/spec.md` | SPEC | 機能仕様（テスタブル粒度） |
| `docs/requirements/what/nfr.md` | NFR | 非機能・制約 |
| `docs/requirements/shared/terms.md` | TERM | 用語・データ辞書 |
| `docs/requirements/analysis/context.md` | ACTOR | 外部アクタ |
| `docs/requirements/analysis/dfd.md` | I, O, P | 入力・出力・論理プロセス |
| `docs/requirements/analysis/events.md` | E | イベント |
| `docs/design/design-behavior/orchestration.md` | ORC | オーケストレーション段 |
| `docs/design/design-behavior/state.md` | DS | データストア |
| `docs/design/design-static/modules.md` | MOD, PORT | モジュール・ポート |
| `docs/design/design-static/types.md` | DM | ドメイン型 |
| `docs/design/design-static/schema.md` | SCM | スキーマ |
| `docs/design/design-static/config.md` | CFG | コンフィグ |
| `docs/design/design-static/prompts.md` | PROMPT | プロンプトテンプレート |
| `docs/verification/test-design.md` | TD | テスト設計 |
| `docs/verification/tests.md` | TC | テストコード |
| `docs/verification/test-results.md` | TR | テスト結果 |
| `docs/verification/doc-verify.md` | VERIFY | ドキュメント検証実施 |
| `docs/verification/findings.md` | FND | 指摘 |
| `docs/decisions.md` *(または分割ファイル)* | DD, Q, PEND | 横断スパイン |

> 上記はデフォルトのパス設計。実際のファイル配置はプロジェクト側で確定し、  
> 検証ツールの設定ファイル（`config.yaml` の `trace_roots` または走査ディレクトリ）に登録する。

---

## 3. トレース対象外ファイル（out-of-graph）

以下のファイルは検証ツールのグラフ走査から**除外**する。

| 種別 | 除外理由 |
|---|---|
| `docs/doc-system/` 配下 | doc-system 自身の設計文書。ノードを含むが自己参照のため別扱い |
| `docs/methods/` 配下 | 手法・プロセス文書。ID ノードを持たない |
| `README.md` 類 | 案内文書。ノード・辺を持たない |
| `CLAUDE.md` | エージェント作業規約 |
| `.claude/` 配下 | スキル・設定ファイル。ノードを持たない |
| `tests/` 配下 | テストコード・ケース・結果の実体。TC/TR ノードは `docs/` 側に記録 |

---

## 4. doc-system 自身のノードについて

`docs/doc-system/02-meta-schema.md` は DD-001〜DD-011 等の確定決定ログを含む。  
これらは「この doc-system の設計における意思決定」であり、review-system 本体のトレース対象ではない。

| 扱い | 内容 |
|---|---|
| **自己管理** | doc-system 内の DD/Q はこの doc-system 自身の設計変更を追跡する |
| **本体適用後** | review-system 本体に doc-system を適用したとき、本体側の DD/Q は別ファイルで管理する |

---

## 5. 走査設定（config.yaml への追加）

検証ツールの走査対象を `config.yaml` で宣言する。

```yaml
# docs/doc-system/config.yaml への追加例

trace_scope:
  include:
    - "docs/requirements/**/*.md"
    - "docs/design/**/*.md"
    - "docs/verification/**/*.md"
    - "docs/decisions.md"
  exclude:
    - "docs/doc-system/**"
    - "docs/methods/**"
    - "**/README.md"
```

> `**` は glob パターン。追加ファイルは `include` に追記する。  
> `exclude` は `include` より優先される。

---

## 6. in-graph 追加の手順

新しいドキュメントファイルをトレース対象に追加するとき：

1. ファイルに `<details><summary>⬡ PREFIX-N` 形式のノードを書く（[04](04-notation.md) 参照）
2. `config.yaml` の `trace_scope.include` に glob パターンを追加（対象外なら不要）
3. 必須辺を記述し、既存ノードへの参照辺が RULE-007 を満たすか確認
4. 検証ツールを走査して ERROR/WARNING がないことを確認

---

## 7. ファイル命名と分割の原則

| 原則 | 内容 |
|---|---|
| 1ファイル＝1責務 | 概念グループを単位とする（FR と SPEC を同じファイルに混在させない） |
| ファイルが大きくなりすぎたら分割 | 1ファイル内のノード数が多くなる場合は `fr-core.md` / `fr-extension.md` のように分割 |
| 分割後のバージョニング | 分割後は新ファイルの version を `1.0.0` から開始する |
| 旧ファイルを消さない（PR8） | 分割前のファイルは `archived/` または `deprecated` 明記で保留 |
