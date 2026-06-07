# 設計 00 — データディクショナリ（集約・正準）

> これまで [process/02 分解](../process/02-decomposition.md) の各プロセスに散在していた `名前 = {要素 + …}` を**1か所に集約**し、
> [05 I/O 台帳](../requirements/05-io-overview.md) の I-#/O-# 型、[11 アダプタ](../requirements/11-platform-adapter.md) のポート契約、
> [13 安定化](../requirements/13-stabilization.md) の異常系/版スタンプ型を足した**正準データ辞書**。
> ここを唯一の真実として [01 クラス設計](01-class-design.md) が型/クラスへ写像する。
>
> 記法：`名前 = { 要素 + 要素 + … }`、`?`=任意、`|`=択一、`{x}`=x の集合（列）、`a → b`=写像。
> **列挙（`|` で閉じた語彙）は Enum 候補、`{…}` の複合は値オブジェクト候補**（[01](01-class-design.md) で確定）。

## 凡例：状態か導出か（[PR5](../methods/method-inventory.md) / [process/03](../process/03-state-inventory.md)）

- **導出（derived）**：毎回作り直せる → 無状態。1実行の産物。**イミュータブルにしやすい**。
- **状態（stateful）**：過去を覚えていないと成立しない（DS1〜DS5）。永続層。

---

## 0. 横断スカラ・列挙（語彙が閉じているもの＝Enum 候補）

| 名前 | 定義 | 値域 | 由来 |
|---|---|---|---|
| `DocumentType` | 文書タイプ | `code \| spec \| minutes \| …`（拡張可） | [02 P1](../process/02-decomposition.md) `型` |
| `Scope` | 適用スコープ | `org`（MVP）`\| team:<名> \| project:<名>` | [02 P1](../process/02-decomposition.md) / [schema](../schema/README.md) |
| `Severity` | 深刻度（順序あり） | `error > warning > info` | [schema](../schema/README.md) |
| `Determinism` | 決定性（基準作者が宣言） | `deterministic \| tradeoff \| judgment` | [schema](../schema/README.md) |
| `OverrideRule` | 上書き方向ゲート | `locked \| tighten-only \| open` | [schema](../schema/README.md) |
| `ApplicationMode` | 適用モード（仕分け結果） | `auto_fix_log_only(🤖) \| auto_fix_suggest(✋) \| human_only(💬)` | [02 P4](../process/02-decomposition.md) `mode` |
| `TriageBucket` | 提示区分 | `auto(🤖) \| approve(✋) \| judge(💬) \| unclassified(❓)` | [02](../process/02-decomposition.md) |
| `ReviewDecision` | 指摘への判断（I-6/I-7） | `approve \| modify \| reject \| out_of_scope` | [02 P6](../process/02-decomposition.md) |
| `ContentHash` | 矛盾/既出判定キー | `hash(対象ルールのメタ + 本文)` | [schema](../schema/README.md#警告の既出判定warning-ledger) |

> ⚠ **基本型の濫用を避ける**（[01](01-class-design.md) 命名/型方針）：`ContentHash`・`RuleId`・`Provenance` 等は
> 生 `str` でなく**値オブジェクト**にして取り違えを型で防ぐ（[01 §2](01-class-design.md)）。**パスは `pathlib.Path`**（自前ラッパは作らない・[DD13](decisions.md#dd13--自前-filepath-クラスの要否オーナー指摘)）。

---

## 1. 受付・正規化（P1 / I-1,I-2,I-3,I-13,I-15）

| 名前 | 定義 | 状態/導出 | 由来 |
|---|---|---|---|
| `提出物 Submission` | `{ 文書群 + 参照群? + 型上書き? + scope指定? }` | 導出（1実行の入力束） | [02 P1](../process/02-decomposition.md) |
| `文書群 / 参照群` | `{ ファイル }`（ファイルパスの列） | 導出 | [02 P1](../process/02-decomposition.md) |
| `ファイル SourceFile` | `{ パス Path + 内容 + (言語?) }` | 導出 | I-1 |
| `型推定 TypeEstimation` | `{ 候補 DocumentType + 確信度 }`（PF＝I-15） | 導出（PF 出力＝入力） | [02 P1.1](../process/02-decomposition.md) |
| `確定型 ResolvedDocumentType` | I-2 上書き と I-15 推定を調停した1つの `DocumentType` | 導出 | [05](../requirements/05-io-overview.md) |
| `対象集合 TargetSet` | `{ ファイル }`（評価する物） | 導出 | [02 P1.3](../process/02-decomposition.md) |
| `参照集合 ReferenceSet` | `{ ファイル }`（突き合わせる物・**評価しない**） | 導出 | [02 P1.3](../process/02-decomposition.md) |
| `正規化入力 NormalizedIntake` | `{ 対象集合 + 参照集合 + 確定型 + scope }`（P1 の出力＝後段の前提） | 導出 | [02 P1](../process/02-decomposition.md) |

---

## 2. 基準合成（P2 / I-4 基準）

| 名前 | 定義 | 状態/導出 | 由来 |
|---|---|---|---|
| `基準ファイル CriteriaFile` | `{ フロントマター + 本文セクション{} }`（DS1・系外編集） | **状態（DS1・永続）** | [schema](../schema/README.md) |
| `フロントマター Frontmatter` | `{ doc_type + scope + extends? + version + rules{} }` | 状態（DS1 内） | [schema](../schema/README.md) |
| `ルール定義 RuleDefinition` | `{ id RuleId + title + category + severity + determinism + enabled + override }` | 状態（DS1 内） | [schema](../schema/README.md) |
| `ルール本文 RuleGuidance` | `{ id + 説明本文 + チェック観点{} + 良い例{} + 悪い例{} }`（人＆LLM 共用） | 状態（DS1 内） | [schema](../schema/README.md) |
| `合成ルール ComposedRule` | `{ id + title + 本文 + 例 + メタ + provenance }` | 導出（毎回合成） | [02 P2](../process/02-decomposition.md) |
| `メタ RuleMeta` | `{ determinism + severity + override + enabled }`（**LLM へ渡さない**） | 導出 | [02 P2](../process/02-decomposition.md) |
| `provenance Provenance` | `{ 由来ファイルパス + 継承段(org\|team\|project) }` | 導出 | [schema](../schema/README.md) / [Q10](../dashboard.md) |
| `観点パック CriteriaPack` | `{ (id + title + 本文 + 例) }`（メタ抜き＝PF へ渡す公開項） | 導出 | [02 P2.3](../process/02-decomposition.md) |
| `メタ表 MetaIndex` | `{ id → (determinism + severity + override + provenance) }`（機械が使う内部表） | 導出 | [02 P2.3](../process/02-decomposition.md) |
| `警告候補 WarningCandidate` | `{ 種別(緩め拒否\|矛盾\|衝突) + rule_id + content_hash + provenance }` | 導出 | [02 P2](../process/02-decomposition.md) |
| `矛盾判定 ContradictionVerdict` | `{ content_hash → (矛盾 yes/no + 理由?) }`（DS2 キャッシュ） | **状態（DS2・捨ててよい）** | [schema](../schema/README.md) |

> **メタ表は導出物**（[PR5](../methods/method-inventory.md)）。`scope`/`severity`/`determinism` 等フロントマター項目は
> `基準ファイル` の中身であり、別状態にしない（[process/03](../process/03-state-inventory.md)）。

---

## 3. 評価（P3 / L1）

| 名前 | 定義 | 状態/導出 | 由来 |
|---|---|---|---|
| `プロンプト ReviewPrompt` | `{ 役割制約 + 観点パック + 対象 + 参照 + 出力スキーマ }` | 導出 | [02 P3.1](../process/02-decomposition.md) |
| `指摘 Finding` | `{ rule_id RuleId + location + (quote?) + rationale + (suggested_fix?) }` | 導出（PF 生成＝入力→検証後 O-2） | [02 P3](../process/02-decomposition.md) |
| `位置 Location` | `{ file Path + (line_range?) }`（**file 必須**） | 導出 | [02 P3](../process/02-decomposition.md) |
| `行範囲 LineRange` | `{ 開始行 + 終了行 }` | 導出 | （新規・タプル回避） |
| `未分類指摘 UnmatchedFinding` | `{ description + location + (suggested_fix?) + 由来(id外れ\|自己申告) }` | 導出（O-7） | [02 P4](../process/02-decomposition.md) / [Q7](../dashboard.md) |
| `修正案 SuggestedFix` | `{ 説明 + diff }`（LLM 原案 or ツール生成の素） | 導出 | [02 P3/P5](../process/02-decomposition.md) |

---

## 4. 検証・仕分け（P4）

| 名前 | 定義 | 状態/導出 | 由来 |
|---|---|---|---|
| `仕分け済指摘 TriagedFinding` | `{ finding + mode ApplicationMode }`（→ bucket は mode から決定的に導出） | 導出 | [02 P4.3](../process/02-decomposition.md) |
| `仕分け結果集合 TriageResult` | `{ auto{} + approve{} + judge{} + unclassified{} }`（4区分の束） | 導出 | [02 P4](../process/02-decomposition.md) |

---

## 5. 適用・レポート（P5 / O-1..O-6）

| 名前 | 定義 | 状態/導出 | 由来 |
|---|---|---|---|
| `finding_id FindingId` | `{ rule_id RuleId + location Location }`（revert/コミット粒度） | 導出（決定的キー） | [02 P5](../process/02-decomposition.md) / [Q3](../dashboard.md) |
| `確定fix ResolvedFix` | `{ finding_id + 生成元(tool\|llm) + diff }` | 導出 | [02 P5.1](../process/02-decomposition.md) |
| `適用コミット AppliedCommit` | `{ finding_id + commit参照 + 適用時刻 }`（DS3 finding-commit） | **状態（DS3・永続）** | [process/03](../process/03-state-inventory.md) / [Q3](../dashboard.md) |
| `衝突群 FixConflict` | `{ location + 競合する確定fix{} }`（同一箇所） | 導出 | [02 P5.2](../process/02-decomposition.md) / [Q20](../dashboard.md) |
| `評価レポート ReviewReport` | `{ auto済{} + ✋diff{} + 💬原案{} + ❓未分類{} + サマリ + 版スタンプ }` | 導出（O-1） | [02 P5.3](../process/02-decomposition.md) / [S6](../requirements/13-stabilization.md) |
| `サマリ ReportSummary` | `{ 区分別件数 + 適用件数 + revert可否 }` | 導出 | [02 P5.3](../process/02-decomposition.md) |
| `revert要求 RevertRequest` | `{ 対象: finding_id \| 実行ID \| all }`（I-14 候補） | 導出 | [02 P5.4](../process/02-decomposition.md) / [G4](../process/04-gaps-found.md) |
| `revert結果 RevertOutcome` | `{ 戻した finding_id{} + 結果状態 }`（O-6） | 導出 | [02 P5.4](../process/02-decomposition.md) |

---

## 6. 育成・ガバナンス（P6 / O-9,O-11,O-12）

| 名前 | 定義 | 状態/導出 | 由来 |
|---|---|---|---|
| `フィードバック Feedback` | `{ finding_id + 判断 ReviewDecision + 時刻 }` | **状態（DS5・永続）** | [02 P6.1](../process/02-decomposition.md) |
| `観点FB提案 GuidanceFeedbackProposal` | `{ 対象rule_id + 変更案 + 根拠 }`（O-12） | 導出（PF 草案→整形） | [02 P6.2](../process/02-decomposition.md) |
| `基準ひな形 CriteriaTemplate` | `{ doc_type + scope + 草案ルール{} }`（O-11） | 導出 | [02 P6.4](../process/02-decomposition.md) |
| `警告レジャー項 WarningLedgerEntry` | `{ rule_id + content_hash + first_seen }` | **状態（DS4・永続）** | [schema](../schema/README.md#警告の既出判定warning-ledger) |
| `警告 Warning` | `{ 種別 + rule_id + content_hash + provenance }`（O-9・新規のみ発行） | 導出 | [02 P6.5](../process/02-decomposition.md) |

---

## 7. 自動化ポリシー（I-5）

| 名前 | 定義 | 状態/導出 | 由来 |
|---|---|---|---|
| `ポリシー AutomationPolicy` | `{ scope + extends? + version + matrix + overrides{} }`（DS1 内・別ファイル） | **状態（DS1・永続）** | [schema](../schema/README.md#自動化ポリシーファイル) |
| `モード写像 ModeMatrix` | `{ (determinism × severity) → ApplicationMode }` | 状態（ポリシー内） | [schema](../schema/README.md) |
| `ポリシー例外 PolicyOverride` | `{ rule_id → ApplicationMode }`（matrix より優先） | 状態（ポリシー内） | [schema](../schema/README.md) |

---

## 8. 異常系（S3 / O-14）

| 名前 | 定義 | 状態/導出 | 由来 |
|---|---|---|---|
| `異常系通知 FailureNotice` | `{ stage 段 + reason 事由 + 対象(ファイル/対象) + 次手 }`（O-14） | 導出（fail-close 出力） | [13 S3](../requirements/13-stabilization.md) / [Q17](../dashboard.md) |
| `処理結果 StageOutcome<T>` | `成功(T) \| 失敗(FailureNotice)`（各段が返す・**例外で落とさず型で表す**） | 導出 | [13 S1/S3](../requirements/13-stabilization.md) |
| `lint 結果 CriteriaLintResult` | `{ 妥当 \| 違反{ ファイル + 行 + 理由 } }`（S5・パーサ兼検証器） | 導出 | [13 S5](../requirements/13-stabilization.md) / [Q5a](../dashboard.md) |

> `StageOutcome<T>` は S3 の「fail-close を例外でなく**値**で表す」ための共通ラッパ（[01 §6](01-class-design.md) で `Result` 型として実装）。

---

## 9. 版スタンプ・provenance（S6）

| 名前 | 定義 | 状態/導出 | 由来 |
|---|---|---|---|
| `版スタンプ ProvenanceStamp` | `{ pf_id + model_id + プロンプト雛形版 + 基準content_hash + 実行時刻 }` | 導出（レポートに記録） | [13 S6](../requirements/13-stabilization.md) |

---

## 10. アダプタ・PF 境界（11 / L1–L6）

| 名前 | 定義 | 状態/導出 | 由来 |
|---|---|---|---|
| `PF能力 PlatformCapabilities` | `{ 構造化出力 + ファイル適用 + ツール実行 }`（各 bool・アダプタが宣言） | 導出 | [11](../requirements/11-platform-adapter.md) |
| `評価要求 ReviewRequest` | `{ 観点パック + 対象 + 参照 + 出力スキーマ }`（ポート入力・L1） | 導出 | [11](../requirements/11-platform-adapter.md) |
| `評価応答 ReviewResponse` | `{ findings{} + unmatched{} }`（ポート出力・**検証前＝信用しない**） | 導出 | [11](../requirements/11-platform-adapter.md) |
| `矛盾判定要求/応答` | `{ 兄弟本文ペア } → { 矛盾 yes/no + 理由? }`（L2） | 導出 | [10](../requirements/10-llm-system-boundary.md) |
| `型推定要求/応答` | `{ 特徴 } → TypeEstimation`（L3） | 導出 | [10](../requirements/10-llm-system-boundary.md) |
| `衝突マージ要求/応答` | `{ 衝突群 } → { 統合fix \| 迷いフラグ }`（L4・2段構え1段目） | 導出 | [10](../requirements/10-llm-system-boundary.md) / [Q20](../dashboard.md) |

> **ラップ境界**（[PR1](../methods/method-inventory.md)）：`ReviewResponse` 等 PF 生成物は**入力**。
> システムが検証/仕分け/整形した後（`Finding`→`O-2`、`TriageResult`→`O-1`）が**出力**。

---

## 集約で見えたこと（[01 クラス設計](01-class-design.md) への申し送り）

1. **閉じた語彙が9種**（§0）＝すべて **Enum** にしてタイプセーフに（生 `str` 比較を排除）。
2. **`{…}` 複合は値オブジェクト**：`Location`/`FindingId`/`Provenance`/`RuleMeta` 等。**タプルにしない**（`(file, line)` のような位置情報は `Location` に）。
3. **導出物は frozen（イミュータブル）にしやすい**：`Finding`・`ComposedRule`・`ReviewReport` 等は1実行の産物で書き換えない。
4. **状態（DS1〜DS5）だけが可変/永続**：`AppliedCommit`(DS3)・`WarningLedgerEntry`(DS4)・`Feedback`(DS5)・`CriteriaFile`(DS1)。
5. **失敗は型で表す**：`StageOutcome<T>`＝`Result` 型で fail-close（[S3](../requirements/13-stabilization.md)）を例外に頼らず表現。
6. **同じ `str` でも意味が違うキー**（`RuleId`/`ContentHash`）は**取り違え防止のため別値オブジェクト**にする（パスは `pathlib.Path`）。
</content>
