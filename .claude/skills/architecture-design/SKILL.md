---
name: architecture-design
description: Design the PHYSICAL module/dependency architecture from a SETTLED logical DFD + domain model — hexagonal ports & adapters, dependency-inward, a single composition root, the CLI/interface surface with exit codes, platform/protocol ports + a driven protocol, and persistence repository ports with transactions. Use AFTER structured-analysis (logical decomposition) and domain-model. NOT logical DFD decomposition (use structured-analysis), NOT external file-format schema (use schema-design).
---

# アーキテクチャ設計（論理 DFD → 物理モジュール/依存・IF・プロトコル・永続）

> 確定した**論理 DFD**（structured-analysis）と**ドメイン型**（domain-model）を、**実装の境界**＝物理アーキテクチャに写す。
> 一体で扱う理由：1〜4 はすべて「**ports & adapters の境界設計**」（モジュール境界・外部IF・PFプロトコル・永続）で、同じ依存規則に従う。
> 原則：[spec-principles](../spec-principles/SKILL.md)（PR1 もので分ける／PR2 機構と運用を混ぜない／PR6 価値経路）。

## 参照（前提が確定していること）
- 論理プロセス分解（DFD L1–Ln）＝structured-analysis の出力。
- 型安全ドメインモデル＝domain-model の出力。
- 外部ファイル形式が要るなら schema-design（本スキルは**形式**でなく**境界**を設計）。

## 手順
1. **依存規則を1枚で固定**：`domain ← core(ports) ← adapters/persistence/io`。**依存は内向きのみ**、`core` は副作用（IO/ネット/外部）を**ポート越し**にしか触らない。**合成ルートは1つ**（結線だけ）。
2. **DFD プロセス → モジュール対応表**：各 L1 プロセスを `core/<usecase>` に、データストアを `ports/repositories` に、外部システム（PF/LLM）を `ports/<port>＋adapters` に割る。
3. **外部アクタ IF（②）**：アクタ操作を入口（CLI サブコマンド等）の**シグネチャ**に。**境界の内側で即ドメイン型へ写像**（生 str を core に流さない）。**終了コード/異常通知**を定義し、I/O 台帳の各 I-#/O-# に対応づける。
4. **プラットフォーム/プロトコル（B）**：副作用・外部判断を**抽象ポート**に。必要なら**駆動プロトコル**（制御を握る側／従う側）と**公開ツール**（決定的処理を外へ）を定義。能力差は系が吸収・**能力宣言**で最低要件を固定。
5. **永続層（C）**：状態（structured-analysis の状態インベントリ）を**リポジトリ port**の裏に隔離。**保存形式**（追記専用/キャッシュ/トランザクション）と**実体**（git 等の枯れた機構）を選ぶ。読み出し1件は frozen。
6. **実行/インポート規約**：正しい package 構造＋絶対 import＋`python -m` 起動。**`sys.path` ハックを使わない**（起点依存で壊れ・依存可視性を損ね・出荷経路と乖離）。

## 判断基準
- **PR1**：論理分解（structured-analysis）と物理写像（本スキル）は別工程。責務が違えば別モジュール。
- **依存は内向き**：core が adapters/io を import したら設計の負け（テスト・差し替え不能）。
- **境界を跨ぐ値はドメイン型のみ**。直和は Enum か `X|Y`、失敗は `Result`（fail-close を型で強制）。
- **PR2**：機構（ポート・検証・トランザクション）と運用ルール（しきい値等）を混ぜない。
- **DFD→モジュール粒度**：「孫プロセスあり OR 責務が明確に別 → L2 単位分割。孫なし＋同一責務圏 → L1 維持」
  - 孫プロセス（L3 以深）を持つ L2 プロセスは単独モジュールに分割（L3 の存在 = その L2 が単独責務を持つ十分な複雑度の証拠）
  - 孫がなくても責務が別圏（例: 変換パイプライン vs ビュー工場・パース vs 射影）なら分割する
  - 密結合直列パイプライン（各ステップの出力が次の入力）は同一責務圏として L1 単位に集約してよい
  - 横断関心事（suppress/scheduled/activate_stage の一元管理等）は L2 だが孫なしでも単独モジュールとする例外

## 点検観点（done）
- 依存規則が1枚にあり、core に具体 import が無い。合成ルートが1つ。
- DFD プロセス／状態が**漏れなく**モジュール／ポートに対応。
- 各 I-#/O-# が IF（入口/出口）のどこかで消費/生成される（孤児なし＝PR6）。
- 安定化策（検証・安全側・fail-close・トランザクション・lint・版）の**所在**が明示。
- 外部出力（LLM 等）が**必ず系の検証を通る**経路になっている（直行経路が無い）。

## 成果物テンプレ
- 依存規則図（mermaid）＋パッケージ構成＋「DFD→モジュール」「S#→所在」対応表。
- IF：サブコマンド表（アクタ/役割/入力/出力・exit）＋シグネチャ＋I/O 台帳対応。
- プロトコル：ポート Protocol ＋能力宣言＋（あれば）駆動プロトコルのディレクティブ表。
- 永続：リポジトリ port ＋ 保存形式 ＋ トランザクション手順 ＋ state 配置。

## ノード著作（MOD / PORT / PRS / DS）

**フロントマター定義**

```yaml
---
id: MOD-1             # 型 prefix + 連番（下表）。採番後は変更禁止
type: MOD             # 型値（下表から選ぶ。自由記述不可）
labels: []            # 任意タグ（post-mvp / experimental 等）。分類用・RULE 判定に影響なし
scheduled: ""         # 空 = 現フェーズ対象。値あり = 後フェーズ予定（全 RULE がサイレント）
suppress: []          # RULE 抑制リスト。inline comment に理由必須。RULE-007 は抑制不可
---
```

| 型 | id PREFIX | 例 |
|---|---|---|
| MOD | `MOD-` | `MOD-1` |
| PORT | `PORT-` | `PORT-1` |
| PRS | `PRS-` | `PRS-1` |
| DS | `DS-` | `DS-1` |

**共通手順**
1. テンプレ複製：`docs/doc-system/templates/design-static/<type>.md`
2. id 採番：上表の PREFIX + 連番（既存最大 +1）。採番後は変更禁止
3. 必須 edges を追加（下表）。`to` が実在する id か確認（RULE-007: always_error）
4. status: pending から始め、反映確認後に done
5. ref_version を参照先の現在 `x.y` に合わせる
6. 受け入れ条件を確認（下表）

| 型 | 必須辺 |
|---|---|
| MOD | → P または → D（プロセス実装＝P・データ型実現＝D・OR・FND-96） |
| PORT | → MOD (refines) |
| PRS（永続） | → DS (refines) |
| DS（データストア） | → P (refines) |
| ORC | → E (trigger) |

**本文フォーマット**

```
# MOD
[モジュールの責務を1文]
**公開 I/F**: [公開する主要な関数・クラス]
**依存**: [依存するポート・モジュール]

# PORT
[ポートの目的（抽象化する副作用・外部判断）]

# PRS
[永続化する対象と保存形式]
**保存形式**: [append-only JSONL / JSON / git 等]
**ライフサイクル**: [作成・更新・削除のタイミング]

# DS
**保存対象**: [何を持つか]
**保存理由**: [なぜ持つか・どこで参照されるか]
**ライフサイクル**: [作成・更新・削除のタイミング]
```

**受け入れ条件**
- [ ] id 一意、type 一致、edges の to がすべて実在（RULE-007）
- [ ] 接続マトリクス ✅ の辺がすべて存在（RULE-006）
- [ ] see-also 辺の status が `n/a`（RULE-014）
- [ ] ref_version が参照先の現在バージョンと一致（RULE-003/004）
</content>
