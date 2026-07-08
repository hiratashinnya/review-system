**status: decided**（2026-07-06 オーナー承認）

> **辺の扱い**: Issue #78 follow-up で SPEC-6-1（`存在しない-id-参照を-rule-007-error-報告`）の condition を `error` から `failure` へ是正済み。未反映シグナルとして残していた `DD→SPEC-6-1` 義務辺は削除し、反映先 SPEC から本 DD への backref へ置換した。昇格元 Q 側も closed 化で `Q→この DD` を張り返すため被参照は確保される（RULE-005 完全孤立を回避）。

**論点**（`always_error 系 SPEC の condition を error か failure に統一するか` より昇格・要約）: `always_error` 系ルール（抑制不可・RULE-005 孤立 / RULE-007 存在しない ID 参照）を検査する SPEC の condition が不揃い（SPEC-6-1=error / SPEC-7=failure）である。FND-83（open・INFO）の指摘を語彙再設計に取り込み、付与基準をどう定めるか。

**決定時の現状**:
- `config.yml` の `always_error: [RULE-005, RULE-007]`（scheduled/suppress/activate_stage いずれでも抑制不可）。
- 対応 SPEC の condition が不揃い:
  - SPEC-6-1「存在しない ID 参照を RULE-007 ERROR 報告」（v0.1.0）→ `condition: error`（傘 SPEC「存在しない ID への参照」の子）。
  - SPEC-7「孤立ノードの検出」（RULE-005・v0.2.0）→ `condition: failure`。
- 両者は同じ always_error 性質だが condition 軸の付与基準が一貫していない。FND-83 が「付与基準を統一定義せよ」と指摘。
- セマンティクス: `failure`＝仕様違反を正しく検出（sad-path）／`error`＝処理不能な異常入力（fail-close 対象）。RULE-005/007 はいずれもパース可能な入力に対しグラフ構造違反を検出する sad-path であり、この観点では両者とも `failure` が自然。一方 always_error（抑制不可・fail-close）という運用面を重視すると `error` にも見える——ここが不揃いの根本。

**選択肢**:
- **A（両者を `failure` に統一・SPEC-6-1 を failure へ）**: 「仕様違反を検出する sad-path」という等価分割の意味を優先。always_error（抑制不可）は condition とは別軸（config の `always_error` リスト）で既に表現済みで、condition を error にする必要はない。
- **B（両者を `error` に統一・SPEC-7 を error へ）**: always_error（fail-close）を condition にも反映。トレードオフ＝error の語彙「処理不能な異常入力」と、RULE-005/007 が扱うもの（入力は処理可能でグラフ構造が違反）がずれ、5値の等価分割セマンティクスが濁る。
- **C（統一せず・付与基準を「検査が扱う入力の性質＝入力等価クラス」で個別判定と規約化）**: condition は always_error 性でなく各 SPEC が扱う入力の等価クラスで決めると規約に明記。A と両立する。
- **D（欠落 condition 用の兄弟 SPEC を新設）**: 各規則が failure/error 両方の兄弟 SPEC を持つべきという前提での新設。**不採用**（下記根拠）。

**推奨**: A（＋C を規約として併記）。ただし根拠は「A/B いずれかへ統一」ではなく「入力等価クラスに基づく個別割当の是正」。

**決定**: **SPEC-6-1（RULE-007 検出・現 `condition: error`）を `failure` へ是正する**。SPEC-7（RULE-005・`condition: failure`）は現状のまま妥当・変更なし。condition の付与基準は「always_error 性（運用属性）」ではなく「各 SPEC が扱う入力の等価クラス」であると規約化する（C を A と併せて明文化）。選択肢 D（欠落 condition 用の兄弟 SPEC 新設）は**不採用**。

**根拠**:
- 当初の「A/B どちらへ統一するか」というフレーミング自体が誤り。正しい基準は**「各 SPEC の condition を、その規則が扱う入力等価クラスに従って個別に正しく割り当てる」**こと。この基準で見ると、SPEC-6-1 の現行 `condition: error` は always_error という運用属性（fail-close・抑制不可）を入力等価クラスに誤って持ち込んだ**誤割当**（always_error は config の `always_error` リスト＋子 SPEC「always_error による抑制不可」で別軸表現済み）。RULE-007 が扱う入力は「パース可能だがグラフ構造が違反（dangling 参照）」＝ sad-path ＝ `failure` クラスが正しい。
- **網羅穴は無い（D 不採用の根拠）**: カバレッジは FR 粒度で規定（RULE-017/018）。`coverage_rules.fr` = `required_conditions: [normal]` / `recommended_conditions: [failure, error]`。RULE-018 は「FR の SPEC 群に failure **も** error **も**存在しない → WARNING」＝ OR セマンティクス（どちらか一方で充足・両方同時保有は非要求）。SPEC-6・SPEC-7 が属する FR「構造的完結性検証」は normal（`整合グラフは構造違反 0 で通過`）／failure（多数の必須辺欠如系）／error（error クラス別 SPEC ファミリー）を既に全網羅済み。
- **RULE-005/007 は各々単一の入力等価クラスしか持たない**: 両規則とも「パース可能な入力に対しグラフ構造違反を検出する sad-path」＝ failure クラスのみ。error クラス（YAML 構文不正・UTF-8 デコード失敗・id 欠如等）は別 SPEC ファミリーが既にカバー済みで、各規則に error 兄弟を新設する必要はない（1 規則 = 1 入力クラスで充足）。∴ オーナーの「failure と error 両方無いと充足していないのでは」という問いへの答えは「このファミリーは failure も error も既に保有し充足している」。

**接続規則変更チェック（FND-99 パターン）**: 本決定は `doc-system-v2/config.yml` の接続規則（`must_link_to` / `must_be_linked_from`）の追加・変更・削除を**含まない**。決定内容は個別 SPEC の `condition` 値の割当基準（入力等価クラス基準）の確定と、その規約明文化であり、辺の接続要否そのものには手を入れない。よって author エージェント・スキル・接続マトリクス・ドキュメント一覧への伝播は不要。

**影響範囲**:
- in-graph（Issue #78 follow-up で反映完了）: 本 DD ノード、昇格元 Q（`always_error 系 SPEC の condition を error か failure に統一するか`）、SPEC-6-1（`存在しない-id-参照を-rule-007-error-報告`）の `condition: failure` 化、FND-83 resolved 化。
- RULE-019 カスケード: 現行 v2 コーパスに SPEC-6-1 を verifies する TD は存在しないため追随変更は不要。
- 傘 SPEC「存在しない ID への参照」の `condition: error` 残存クリーンアップは、Q1（傘表現決定）の follow-up として同時に反映済み。

**覆る場合の影響範囲**: 決定が覆った場合（例: B を採用＝両者を error に統一へ転換）は、本 DD の義務辺 `DD→SPEC-6-1` の意味（error→failure 是正の未反映）を撤回し、SPEC-7 側 condition の変更方針に切り替える。加えて condition 付与基準の規約（入力等価クラス基準）の明文化も差し戻す。昇格元 Q の closed も再オープンが必要になる。
