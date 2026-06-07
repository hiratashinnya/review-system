# 設計判断ログ（Design Decisions / DD#）

> 凍結セット（[README](README.md)）を進める中で**仕様で一意に決まらなかった点**を、原案→比較→理由付き推奨で**暫定決定**した記録。
> 各 DD は `論点／選択肢＋トレードオフ／推奨・非推奨（理由付き）／暫定決定／影響範囲`。
> **暫定**＝合理的デフォルトで前に進めるための仮決め。覆す場合の影響範囲を必ず併記する（PR8 消さない・PR2 機構/デフォルト）。
> 🛑 印は**俺（オーナー）の判断が要る**と判断して停止し打ち上げた項目（末尾「要オーナー判断」へ）。

## 一覧

| DD | 論点 | 暫定決定 | 影響 |
|---|---|---|---|
| DD1 | 人間向けインターフェースの形 | 単一 CLI `reviewer` ＋サブコマンド | [03](03-external-interfaces.md) |
| DD2 | PF 駆動の stdout 制御プロトコル形式 | 行指向ディレクティブ（`>>> ...`）＋ stderr 診断分離 | [04](04-platform-protocol.md)/[08](08-logging-and-versioning.md) |
| DD3 | 決定的ツールの公開トランスポート | CLI サブコマンド（stdin=JSON / stdout=JSON）。MCP は後 | [04](04-platform-protocol.md) |
| DD4 | DS2/DS4/DS5 の保存形式 | append-only JSONL ＋ JSON（stdlib のみ・sqlite 不採用） | [05](05-persistence.md) |
| DD5 | DS3 内部 git ワークスペースの実体 | 実行ごとの作業コピーを `git` subprocess で finding 単位コミット | [05](05-persistence.md) |
| DD6 | `ExecutionId` の定義（クラス設計の穴埋め） | `executed_at + criteria_hash` 由来の実行識別子を新規型に | [05](05-persistence.md)/[01](01-class-design.md) |
| DD7 | プロンプト雛形のバージョニング | 雛形 id ごとの整数版（`role/1`, `review/3`…） | [07](07-system-prompts.md)/[08](08-logging-and-versioning.md) |
| DD8 | 構造化出力の強制（agentic PF のグレーゾーン Q22） | プロンプトで strict JSON 指定＋アダプタで再パース→失敗は ❓未分類 | [07](07-system-prompts.md)/[04](04-platform-protocol.md) |
| DD9 | ログ出力先（stdout が制御に使われる問題） | 制御=stdout・診断ログ=stderr・実行ログ=`run.log`・テストは tee | [08](08-logging-and-versioning.md) |
| DD10 | レビュアーの承認/決定の入口 | `approve`/`decide` サブコマンド＋レポートが finding_id を提示 | [03](03-external-interfaces.md) |

---

## DD1 — 人間向けインターフェースの形
- **論点**：User/Reviewer/Maintainer の操作（提出・revert・承認・決定・FB・ひな形・lint）をどう露出するか。
- **選択肢**：(A) 単一 CLI `reviewer` ＋サブコマンド／(B) 操作ごとに別バイナリ／(C) いきなり Web/TUI。
- **トレードオフ**：A＝1エントリで合成ルート1つ([02](02-module-architecture.md))に合致・テスト容易。B＝分散し共通結線が崩れる。C＝MVP に過剰（[11](../requirements/11-platform-adapter.md) は「UI は後」）。
- **推奨 A（採用）／非推奨 B,C**：理由＝[02](02-module-architecture.md) の「合成ルートは1つ＝`io/cli`」と一致、[11](../requirements/11-platform-adapter.md) MVP 方針（オーケストレータ/UI は後）に整合。
- **暫定決定**：単一 CLI `reviewer <subcommand>`。
- **影響範囲**：`io/cli`。覆す（GUI 先行等）なら 03 全面・合成ルート再設計。

## DD2 — PF 駆動の stdout 制御プロトコル形式
- **論点**：[11](../requirements/11-platform-adapter.md) の「システムが制御フローを stdout に流し、Claude が従う」具体形式。
- **選択肢**：(A) 自由文／(B) 行指向ディレクティブ（`>>> STEP` `>>> CALL` `>>> EXPECT` `>>> DONE`）／(C) JSON-Lines。
- **トレードオフ**：A＝順序を握れるが機械追従が不安定。B＝人間可読＋機械追従可・最小実装。C＝厳密だが Claude Code の自由記述と相性が悪く冗長。
- **推奨 B（採用）／非推奨 A,C**：理由＝[11](../requirements/11-platform-adapter.md)「順序はシステムが握る」を**最小の決め事**で満たせ、人間も読める（MVP は人間も見ている）。
- **暫定決定**：行頭 `>>> ` のディレクティブ集合（[04](04-platform-protocol.md) §プロトコル）。診断は stderr（DD9）。
- **影響範囲**：04/06/08。本番 System 駆動移行時はプロトコルを内部関数呼び出しに置換（ツールは不変）。

## DD3 — 決定的ツールの公開トランスポート
- **論点**：[11](../requirements/11-platform-adapter.md) の公開ツール群（compose/validate/triage/apply/commit/revert…）を PF へどう露出するか。
- **選択肢**：(A) CLI サブコマンド（stdin/stdout JSON）／(B) MCP サーバ／(C) function-calling 直結。
- **トレードオフ**：A＝Claude Code ネイティブ・stdlib のみ・DD1 と同居。B＝将来本命だが MVP に重い。C＝PF 依存。
- **推奨 A（採用）／非推奨 B,C（MVP では）**：理由＝[11](../requirements/11-platform-adapter.md)「CLI＋stdout が最も単純で Claude Code ネイティブ」。同じ関数を後で MCP/System 駆動に再利用。
- **暫定決定**：各決定的ツール＝`reviewer` のサブコマンド。中身は `core` の純関数を呼ぶ薄い殻。
- **影響範囲**：04。MCP 化は殻を足すだけ（core 不変）。

## DD4 — DS2/DS4/DS5 の保存形式
- **論点**：矛盾キャッシュ・警告レジャー・フィードバックの永続形式（[Q5](../dashboard.md) stdlib のみ）。
- **選択肢**：(A) append-only JSONL（＋キャッシュは JSON）／(B) sqlite3（stdlib）／(C) 1枚 JSON を読み書き。
- **トレードオフ**：A＝**追記専用**要件（[schema](../schema/README.md) 警告レジャー append-only・PR8）に構造一致・人間が grep 可・実装最小。B＝クエリ強いが MVP に過剰・スキーマ移行が要る。C＝全書き換えで追記の原子性が弱い。
- **推奨 A（採用）／非推奨 B,C**：理由＝レジャー/FB は本来 append-only（[schema](../schema/README.md)・[13 S6](../requirements/13-stabilization.md)）。DS2 は hash→判定の少数キーなので JSON で十分。
- **暫定決定**：DS4/DS5＝JSONL、DS2＝JSON（hash キー辞書）。配置は [05](05-persistence.md) の state dir。
- **影響範囲**：05/persistence。規模増で sqlite へ移すなら repo 実装のみ差し替え（port 不変）。

## DD5 — DS3 内部 git ワークスペースの実体
- **論点**：[Q3](../dashboard.md) finding 単位コミット・revert・[13 S4](../requirements/13-stabilization.md) all-or-nothing をどう実装するか。
- **選択肢**：(A) 実行ごとに対象を作業コピーへ展開し `git` を subprocess 駆動／(B) `dulwich` 等の純 Python git／(C) 自前の差分スタック。
- **トレードオフ**：A＝stdlib `subprocess`＋本物の git で revert が堅牢・[11](../requirements/11-platform-adapter.md) の作業ディレクトリ同居と一致。B＝外部依存（[Q5](../dashboard.md) 違反）。C＝revert を自作＝S4 のリスク。
- **推奨 A（採用）／非推奨 B,C**：理由＝git の `revert`/`reset` を使えば「finding 単位 revert」「実行単位巻き戻し」が枯れた機構で得られる。git バイナリ前提は社内ツールとして妥当。
- **暫定決定**：`.review-workspace/<exec_id>/` に対象を複製し `git init`→fix ごとに `git commit`。実行内失敗は `git reset --hard` で書込ゼロ（S4）。revert は対象コミットの `git revert`。
- **影響範囲**：05。git 不在環境なら C へ退避が要る（→ 要オーナー判断ではなく前提条件として明記）。

## DD6 — `ExecutionId` の定義
- **論点**：[01 クラス設計](01-class-design.md) は `RevertTarget = FindingId | ExecutionId | All` を参照するが `ExecutionId` 未定義（穴）。
- **選択肢**：(A) `executed_at(ISO) + criteria_content_hash` から導出する明示型／(B) 連番／(C) UUID。
- **トレードオフ**：A＝[13 S6](../requirements/13-stabilization.md) 版スタンプと**同じ素材**で再現性に直結・無状態で導出可。B＝状態（カウンタ）が要る。C＝不透明で版スタンプと結びつかない。
- **推奨 A（採用）／非推奨 B,C**：理由＝S6 の `ProvenanceStamp` と1:1で対応づき、ログ/コミット/revert を串刺しできる（[08](08-logging-and-versioning.md)）。
- **暫定決定**：`ExecutionId(value: str)` 値オブジェクト。`ProvenanceStamp` に `execution_id` を追加。
- **影響範囲**：05/08 と **[01 クラス設計](01-class-design.md)（型追加が要る・本ログで明示）**。`AppliedCommit` も `execution_id` を持つ。

## DD7 — プロンプト雛形のバージョニング
- **論点**：[13 S6](../requirements/13-stabilization.md) の「プロンプト雛形版」の採番。
- **選択肢**：(A) 雛形 id ごとの整数（`review:3`）／(B) semver／(C) ファイル hash。
- **トレードオフ**：A＝読みやすく差分追跡容易・版スタンプに載せやすい。B＝MVP に過剰。C＝人が版を語れない。
- **推奨 A（採用）／非推奨 B,C**：理由＝雛形は少数・線形に育つ。版スタンプ・ログで人が「review:3 で評価」と言える。
- **暫定決定**：`prompts/templates/<id>.md` 先頭に `version: <int>`。`ProvenanceStamp.prompt_template_version` に主たる評価雛形（`review`）の版を載せる。
- **影響範囲**：07/08。

## DD8 — 構造化出力の強制（Q22 グレーゾーン）
- **論点**：agentic PF は JSON 強制が緩い（[11 グレーゾーン](../requirements/11-platform-adapter.md)）。どう固めるか。
- **選択肢**：(A) プロンプトで strict JSON スキーマ指定＋アダプタで再パース／1回再問い合わせ→なお不正は ❓未分類／(B) raw API へ即降格／(C) 自由文を後段で正規表現抽出。
- **トレードオフ**：A＝[13 S1](../requirements/13-stabilization.md)（取りこぼしゼロ・degrade）に一致・MVP の PF 駆動で動く。B＝[11](../requirements/11-platform-adapter.md) の「困ったら降りる」を**最初から**やる＝過剰。C＝壊れやすい。
- **推奨 A（採用）／非推奨 B,C**：理由＝S1 が既に「不正は ❓未分類へ退避」を要求。能力宣言で**構造化出力を必須**（Q22）にしつつ、揺れはアダプタが吸収。
- **暫定決定**：L1 出力スキーマをプロンプトに明示（[07](07-system-prompts.md)）。アダプタは parse→1回 repair 問い合わせ→失敗は ❓未分類。困窮時は port を保って raw API アダプタへ降りる（後）。
- **影響範囲**：07/04。

## DD9 — ログ出力先
- **論点**：PF 駆動では **stdout が制御プロトコル**（DD2）。テスト戦略は「stdout ダンプをログに」と要求。混線する。
- **選択肢**：(A) 制御=stdout／診断=stderr／実行ログ=`run.log`、テストは両者を tee／(B) すべて stdout に混在／(C) 制御も含め全て構造化ログファイルへ。
- **トレードオフ**：A＝チャネル分離で Claude は stdout だけ追え、診断は汚さない・テストは tee で 3点セットのログを満たす。B＝Claude の追従が壊れる。C＝PF 駆動の「stdout で指示」を捨てる。
- **推奨 A（採用）／非推奨 B,C**：理由＝[11](../requirements/11-platform-adapter.md) の stdout 制御と[テスト戦略](../../.claude/skills/test-strategy/SKILL.md)のログ要件を両立。
- **暫定決定**：`io/cli` は制御を stdout、`logging` 診断を stderr、実行単位ログを `.review-workspace/<exec_id>/run.log`。テストは `2>&1 | tee`。
- **影響範囲**：08/04/06。

---

## 要オーナー判断（🛑）
> 現時点で**矛盾・要件欠落による停止は無し**。上記 DD はすべて合理的デフォルトで前進可能と判断。
> 将来オーナー確認が要りそうな種（停止には至らないが影響大）を**先出し**しておく：
> - **前提**：DD5 は **git バイナリの存在**を前提にする（社内ツールとして妥当と判断・暫定採用）。git 無し運用が要件なら DD5-(C) へ。
> - **観測**：[Q9](../dashboard.md) 警告の打ち上げ条件（バッチ/しきい値/dedup）は[schema](../schema/README.md) でも未決。MVP は「既出抑制（DS4）＋新規のみ即時」で前進（[05](05-persistence.md) で機構のみ）。運用ルール詰めは PR2 によりここでは行わない。
</content>
