# 13. 価値実現の安定化（S1–S6 の要件化）

> [dashboard](../dashboard.md#-価値実現の安定化洗い出しs1s6mvps7s9post-mvp) の安定化策 S1–S6 を**実装可能な要件**に落とす。
> P1（出すと仕分けレポートが返る）・P2（直す＋戻せる）を **安定して**届けるための具体物。
> 最大の不安定要因は**唯一の非決定ステップ＝LLM(④)**。ここを固く・失敗を可視化・書込を安全側に倒す。
> 出典：[09 パイプライン](09-processing-pipeline.md) / [10 境界](10-llm-system-boundary.md) / [07 AI入力](07-ai-input-design.md) / [schema](../schema/README.md) / [Q2/Q3/Q7/Q17](../dashboard.md)。

## 位置づけ（MVP 必須 / 推奨）

| S# | 安定化策 | 段階 | 関連 Q / 段 |
|---|---|---|---|
| S1 | LLM 出力の契約検証を固く | **MVP 必須** | Q7・⑤ |
| S2 | 仕分けの安全側デフォルト | **MVP 必須** | Q2・⑥ |
| S3 | 異常系ポリシー（fail-close＋O-14） | **MVP 必須** | Q17・全段 |
| S4 | 自動適用のトランザクション性 | **MVP 必須** | Q3・⑦ |
| S5 | 基準の事前 lint（実行前検証） | MVP 推奨 | Q5a・schema・② |
| S6 | 結果の provenance / 版スタンプ | MVP 推奨 | Q15・⑦⑧ |

> 各 S は **機構（設計）として要件化**する。運用ルール（しきい値・cadence 等）は機構のデフォルトに留め、ここで詰めない（[PR2](../methods/method-inventory.md)）。

---

## S1 — LLM 出力の契約検証を固く（MVP 必須）

**防ぐ事故**：幻覚 `rule_id`・欠損 `location`・壊れた JSON を、crash させる／黙って捨てる（silent-drop）こと。

**要件**
- ⑤正規化&検証（[09](09-processing-pipeline.md)）は、PF/アダプタが返した生出力を **strict なスキーマ**で検証する。
  - `finding = { rule_id + location(file 必須) + rationale + (quote? / suggested_fix?) }`（[design/00](../design/00-data-dictionary.md)）。
- 非適合（スキーマ違反・`location.file` 欠落・パック外 `rule_id`）は **crash も silent-drop もしない**。
  必ず **`❓未分類`（O-7）へ退避**して surfacing する（取りこぼし＝偽の安心を作らない）。
- `rule_id` 検証は②で送った**観点パックに実在するか**で機械判定（[09](09-processing-pipeline.md)⑤-1）。
- 検証は**仕分け（⑥）・自動適用（⑦）より前**（順序の不変条件）。

**受け入れ基準**
- 壊れ JSON / 幻覚 id / location 欠落 の各ケースで、**例外で停止せず**、当該 finding が `❓未分類` に入りレポートに出る。
- 有効 finding 数 ＋ 未分類数 ＝ LLM が出した item 数（**取りこぼしゼロ**の保存則）。

---

## S2 — 仕分けの安全側デフォルト（MVP 必須）

**防ぐ事故**：`determinism` の誤宣言・未宣言由来で、人が見るべき指摘が誤って 🤖 自動適用されること。

**要件**
- 仕分け（⑥）は `rule_id → メタ(determinism×severity) → ポリシー → mode` で機械判定（[02](../process/02-decomposition.md) P4.3）。
- **`determinism` が未宣言／不明／パース不能のルールは、🤖 にしない**。既定で**人間側（✋ suggest / 💬 human_only）**へ倒す。
  - 既定の安全側 mode は **`human_only`（💬）**。「決定的と確証が持てないものは人へ」。
- この安全側フォールバックは**ポリシー matrix の有無に依存しない**（matrix 欠落時も 🤖 を生まない）。

**受け入れ基準**
- `determinism` キーを欠いた／未知値のルールの finding は、**🤖 区分に出ない**（✋ または 💬 に入る）。
- ポリシー matrix が当該 `determinism×severity` を持たない場合も、**自動適用は発生しない**。

---

## S3 — 異常系ポリシー（fail-close＋O-14）（MVP 必須・Q17 確定）

**防ぐ事故**：部分結果での誤適用・「網羅した」という偽の安心。

**原則**：価値経路は遮断しないが**誤った結果は出さない**。**疑わしきは fail-close＋明示エラー（O-14）**。
fail-open は「続けてもリスクが無い良性ケース」（＝空文書）に限る。
自動適用⑦は**完全・クリーンな ④/F4 を前提**とし、上流失敗時は**一切書き込まない**（半端を残さない＝ステートレス）。

**段ごとの振る舞い（MVP）**

| 異常(E14) | 段 | 振る舞い | post-MVP(F16) |
|---|---|---|---|
| 基準パース失敗 | ②合成 | **fail-close**：レビュー中止＋O-14（どのファイル/なぜ）。org 少数ファイルなので全体停止で安全 | 当該ファイルのみ skip＋「N/M 適用」明示の degrade |
| LLM 障害（PF 到達不可/タイムアウト） | ④評価 | **bounded retry → fail-close**：findings 無し＝価値無し。**⑦自動適用は走らせない**。O-14 明示 | バッチ単位で部分 degrade |
| LLM 出力が不正（schema 違反/偽 rule_id） | ⑤検証 | **degrade（S1）**：不正 finding は ❓未分類へ。crash/silent-drop 禁止 | 同左（強化） |
| スコープ未解決（doc_type 不明 / `extends` 切れ / 基準ゼロ） | ①② | **fail-close＋実行可能エラー**：「doc_type=X の基準が無い／extends 先が無い」。空の既定にフォールバックしない | 切れた継承リンクを名指しで surfacing |
| 空文書（評価対象が実質ゼロ） | ①intake | **fail-open（良性 no-op）**：0件レポート「評価対象なし」。エラーにしない | 同左 |

**要件**
- 上表の各失敗点は **`O-14 異常系エラー通知`** を生成する：`{ stage + reason + 該当ファイル/対象 + 実行可能な次手 }`（[design/00](../design/00-data-dictionary.md)）。
- O-14 は**黙って空結果にしない**＝「読めなかった/評価できなかった」を必ず可視化（偽の安心の禁止）。
- ⑦自動適用の**前提条件＝④/⑤がクリーンに完了**。未達なら書込ゼロ（DS3 に何もコミットしない）。
- **横断モデル**：この fail-close は特定プロセス内の正常データフローではなく**横断的エラー経路**として扱う（[process/04 G7/G10](../process/04-gaps-found.md)・[process/00 異常系の横断モデル](../process/00-context.md)）。

**受け入れ基準**
- 基準パース失敗・LLM 障害・スコープ未解決の各ケースで、**部分適用が起きず**（DS3 無変更）、O-14 が理由付きで返る。
- 空文書では O-14 を出さず、0 件レポートが返る。
- LLM 障害時、⑦は一度も書込まない。

---

## S4 — 自動適用のトランザクション性（MVP 必須）

**防ぐ事故**：半端な書き換えがファイルに残る（戻せない自動修正）。

**要件**
- 🤖 自動適用（⑦）は **finding 単位で1コミット**（`finding_id = rule_id + location`・[Q3](../dashboard.md)）。DS3（内部 git ワークスペース）に積む。
- **失敗時は書込ゼロ**：1 実行内のいずれかの fix 適用が失敗したら、その実行ぶんは**適用済みも含めて巻き戻す**（all-or-nothing は実行単位、revert 粒度は finding 単位）。
- **常に revert 可**：個別 finding／実行ぶん一括／全体 を、対象コミット群の revert で戻せる（O-6）。
- 同一箇所に重なる fix は**衝突解決**（[Q20](../dashboard.md) 2段：LLM マージ→迷いは人）してから適用（[02](../process/02-decomposition.md) P5.2）。

**受け入れ基準**
- 適用途中で1件失敗 → その実行の書込が**ファイルに残らない**（DS3 / 作業ツリーがクリーン）。
- 任意の適用済み finding を指定して revert → 当該変更だけが戻り、他は残る。
- 実行 ID 指定の一括 revert → その実行の全 finding コミットが戻る。

---

## S5 — 基準の事前 lint（実行前検証）（MVP 推奨・Q5a と一体）

**防ぐ事故**：E14（基準パース失敗・不正 override・extends 切れ）を**実行時**に踏むこと。**作成時**に倒す。

**要件**
- **自前フロントマターパーサが検証器を兼ねる**（[Q5a](../dashboard.md) / [schema 対応文法](../schema/README.md#対応フロントマター文法自前パーサが読むサブセットq5a)）。lint 項目：
  - フロントマター文法が**対応サブセット内**か（範囲外記法 → fail-close）。
  - `override ∈ {locked, tighten-only, open}`／`severity ∈ {error, warning, info}`／`determinism ∈ {deterministic, tradeoff, judgment}`。
  - `extends` 先が存在するか（継承リンク切れ検出）。
  - 必須キー（`doc_type` / `scope` / `rules[].id`）の存在・`id` の一意性。
- lint 失敗は **O-14 と同形式**（ファイル/行/理由）で返す。

**受け入れ基準**
- 不正な `override` 値・未対応記法・extends 切れの各基準ファイルを、**レビュー実行前**に名指しで弾ける。

---

## S6 — 結果の provenance / 版スタンプ（MVP 推奨）

**防ぐ事故**：「なぜこの結果になったか」が説明不能・再現困難になること。

**要件**
- レポート（O-1）に**版スタンプ**を記録：`{ pf_id + model_id + プロンプト雛形版 + 基準の content_hash + 実行時刻 }`（[design/00](../design/00-data-dictionary.md)）。
- 各 finding/ルールに **provenance（由来ファイルパス・継承段）**を保持（[Q10](../dashboard.md)・既設）。

**受け入れ基準**
- 同一入力・同一版で再実行したとき、版スタンプから**どの基準・どの PF/モデル・どの雛形**で評価したか追える。

---

## まとめ

- **MVP に必ず入れる**：S1（受け口を固く）・S2（安全側仕分け）・S3（fail-close＋O-14）・S4（トランザクション）。
- **MVP 推奨**：S5（事前 lint＝パーサ兼検証器）・S6（版スタンプ）。
- 共通思想：**唯一の非決定（LLM）を機械で受け止め、失敗は可視化し、書込は安全側に倒す**。
  これが「LLM をラップして価値を出す」システムの**信頼の構造的担保**（[10 不変条件](10-llm-system-boundary.md)）。
</content>
</invoke>
