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
| DD7 | プロンプト/コンフィグのバージョニング | **`MAJOR.MINOR`**（MAJOR=構造/型変更→ロジック改修要・MINOR=内容/文言のみ）。**対応版はパーサ側に定数で持つ** | [07](07-system-prompts.md)/[08](08-logging-and-versioning.md)/[schema](../schema/README.md) |
| DD8 | 構造化出力の強制（agentic PF のグレーゾーン Q22） | プロンプトで strict JSON 指定＋アダプタで再パース→失敗は ❓未分類 | [07](07-system-prompts.md)/[04](04-platform-protocol.md) |
| DD9 | ログ出力先（stdout が制御に使われる問題） | 制御=stdout・診断ログ=stderr・実行ログ=`run.log`・テストは tee | [08](08-logging-and-versioning.md) |
| DD10 | 承認/決定/FB の入口（100件問題） | **インタラクティブ HTML レポート**にチェックボックス入力。`decide`/`feedback`/`approve` は**レポートのパスだけ**を引数に取る | [03](03-external-interfaces.md)/[06](06-orchestration.md) |
| DD11 | 観点FB起草(P6.2/O-12) のオンデマンド起動口 | `criteria feedback-draft` を論理追加・**MVP保留印** | [03](03-external-interfaces.md)/[06](06-orchestration.md) |
| DD12 | lint/revert 失敗の O-14 語彙 | `FailureStage` に `LINT` 追加・revert 対象なしは exit2（stage 不要） | [01](01-class-design.md)/[03](03-external-interfaces.md) |
| DD13 | 自前 `FilePath` クラスの要否 | **廃止し `pathlib.Path`（stdlib）を使う**。突合キーは intake で正規化 | [01](01-class-design.md) |
| DD14 | HTML レポート→CLI の往復（サーバ無し） | レポート内 JS が**フィードバック JSON を書き出し**、コマンドは review_id で同梱ファイルを解決 | [03](03-external-interfaces.md) |
| DD15 | `ReviewReport` の形（実装時） | P1 は仕分け4区分（auto/approve/judge/unclassified）＋summary＋stamp を持つ。`applied`(ResolvedFix) は **P2(apply) で追加** | [01](01-class-design.md)/report.py |
| DD16 | Q24 解決＝パーサ拡張（オーナー決定 A） | mini-YAML に**引用キー（`"*"`）＋3段ブロックネスト**を追加（flow は非対応のまま）。policy はブロック形。schema の文法表/例を先に更新してから実装 | [schema](../schema/README.md)/parsing |

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

## DD7 — プロンプト/コンフィグのバージョニング（**オーナー指示で改訂**）
- **論点**：[13 S6](../requirements/13-stabilization.md) の「プロンプト雛形版」＋コンフィグ（基準/ポリシー）版の採番。**構造が変わると対応ロジックを変えねばならず、版から対応ロジックが一目で分かること**が要件（オーナー指示）。
- **選択肢**：(A) 単一整数／(B) **`MAJOR.MINOR`**（MAJOR=構造/型・MINOR=内容）／(C) フル semver(`x.y.z`)。
- **トレードオフ**：A＝構造変更とロジック改修の対応が版に出ない（要件未達）。B＝**MAJOR↔対応ロジック**が一目・最小で足りる。C＝patch まで要らず過剰。
- **推奨 B（採用）／非推奨 A,C**：理由＝オーナー要件「型変わったら MAJOR・文章だけなら MINOR」に一致。MAJOR を**処理ロジックの世代キー**にし、版↔ロジック対応表を持てる（[07](07-system-prompts.md)/[08](08-logging-and-versioning.md)）。
- **暫定決定（確定）**：版は最低 `MAJOR.MINOR`。**MAJOR 改 ⇔ 構造/型変更 ⇔ 対応パーサ/ビルダー改修必須**。MINOR 改＝本文/文言のみ（ロジック不変）。プロンプト雛形・基準フロントマター・ポリシーすべてに適用。`ProvenanceStamp.prompt_template_version`＝`"review:3.1"` 形式。**未対応 MAJOR は S5 fail-close**、MINOR 差は許容（情報のみ）。
- **影響範囲**：07/08／[schema](../schema/README.md) の `version` フィールド／[13 S5/S6](../requirements/13-stabilization.md)。

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

## DD10 — 承認/決定/FB の入口（**オーナー指摘で全面改訂**：100件問題）
- **論点**：✋承認・💬決定・FB を finding 単位で **CLI に id を打って**渡すのは、100件出たら破綻＝非現実的（オーナー指摘）。
- **選択肢**：(A) ~~`approve <exec> <finding…>` 等 id 列挙~~（**却下**：UX 破綻）／(B) **インタラクティブ HTML レポート**にチェックボックスで入力し、コマンドは**レポートのパスだけ**を取る／(C) 対話 TUI で1件ずつ。
- **トレードオフ**：A＝大量時に使い物にならない。B＝**UI をブラウザに委譲**でき、id 入力ゼロ・一覧で一括操作・コマンドは1引数で済む。C＝端末で重く、大量時も遅い。
- **推奨 B（採用）／非推奨 A,C**：理由＝レビューとレポートは**1:1**。レポートに **`review_id`（=`ExecutionId`）を埋め**、各 finding に入力欄を持たせれば、人はブラウザで選ぶだけ。`decide`/`feedback`/`approve` は**レポートのパスだけ**で対象（review_id と各 finding の入力）が解決する。
- **暫定決定（確定）**：
  - **O-1 レポート＝インタラクティブ HTML**。finding ごとに `承認/却下/対象外/決定` のチェックボックス＋（💬 用）任意の修正欄。
  - レポートに **`review_id` を埋め込み**（表示は任意）。**DS3 修正適用フォルダ `.review-workspace/<review_id>/` にも同 id を持つ**（既に exec_id キー）。
  - `decide`/`feedback`/`approve` の**引数はレポートのパスのみ**。往復方式は [DD14](#dd14--html-レポートcli-の往復サーバ無し)。
- **影響範囲**：03（コマンド簡素化）・06（レポート→人→コマンドのループ）・[01](01-class-design.md)（`ReviewReport` の HTML レンダリング＋`review_id`）。

## DD13 — 自前 `FilePath` クラスの要否（**オーナー指摘**）
- **論点**：[01](01-class-design.md) は `FilePath` を**検証なしの str ラッパ**として定義。`RuleId` 等との取り違え防止が理由だが、`pathlib.Path` は既に `RuleId` と別型＝取り違え論拠が弱い。要るのか？
- **選択肢**：(A) **廃止して `pathlib.Path`（stdlib）を使う**＋突合キーは intake で正規化／(B) `FilePath` に**仕事を与える**（正規化済みリポジトリ相対 POSIX キーとして検証付き）／(C) 現状維持（ほぼ無価値）。
- **トレードオフ**：A＝パス操作（glob/suffix/join）が**無料**・stdlib・Path は immutable+hashable。突合（参照除外・`location.file`）の厳密性は**正規化関数**で担保。B＝型安全だが薄いラッパの保守コスト。C＝[PR1](../methods/method-inventory.md) primitive 偽装で価値なし。
- **推奨 A（採用）／非推奨 B,C**：理由＝`Path` で取り違えは起きない（`RuleId` と別型）。パス操作が無料で、唯一の懸念（LLM 返却パスの厳密一致・参照集合判定）は **intake での正規化（リポジトリ相対 POSIX 文字列化）** で解決。
- **暫定決定**：`FilePath` を廃し **`pathlib.Path`** を使う。`location.file`・参照集合・finding 突合は **intake で正規化した Path** で行う（正規化は1箇所＝境界）。
- **影響範囲**：[01](01-class-design.md)（`Location.file`/`SourceFile.path`/`Provenance.source_path` を `Path` に・`FindingId` の hash は Path が hashable で不変）・03 の写像（`FilePath(p)` → `Path(p)` ＋ 正規化）。

## DD14 — HTML レポート→CLI の往復（サーバ無し）
- **論点**：[DD10](#dd10--承認決定fb-の入口オーナー指摘で全面改訂100件問題) で「コマンドはレポートパスだけ」。ブラウザで入力した状態を、**サーバを立てずに**どうコマンドへ戻すか。
- **選択肢**：(A) レポート内 **JS が `<review_id>.feedback.json` を書き出し**、コマンドは review_id で同梱ファイルを探す／(B) **ローカルサーバ** `reviewer serve` に POST して即適用／(C) 保存した HTML を再パース（ブラウザはチェック状態を保存しないので不可）。
- **トレードオフ**：A＝サーバ不要・stdlib（HTML/JS を生成するだけ）・「引数はパスだけ」と両立。B＝往復は滑らかだが常駐サーバ＝MVP に重く「コマンドだけ」と乖離。C＝技術的に破綻。
- **推奨 A（採用）／非推奨 B,C**：理由＝[11](../requirements/11-platform-adapter.md) の「軽量・サーバレス」志向に一致。系は HTML＋クライアント JS を出すだけで、状態は JSON で受ける。
- **暫定決定**：HTML レポートに「書き出す」ボタン（JS）＝`<review_id>.feedback.json` をダウンロード。`reviewer feedback/decide/approve <report.html>` は HTML から `review_id` を読み、**同ディレクトリ（または既定の DL 先）から該当 feedback.json を解決**して適用。
- **影響範囲**：03。🛑 **小さな摩擦＝要オーナー確認**：ブラウザの DL 先が既定 Downloads になりがち。許容（ユーザがレポート横へ移動）か、`reviewer serve`（DD14-B）を将来採るかは運用で判断。MVP は A で前進。

## DD11 — 観点FB起草(P6.2) のオンデマンド起動口
- **論点（[spec-inspector G3](README.md)）**：O-12 観点FB提案は port(L5)・雛形(`feedback-draft`)・core 関数が揃うのに、**起動する CLI 口が無い**（`feedback` は DS5 収集どまり）＝価値経路の細い穴（[PR6](../methods/method-inventory.md)）。
- **選択肢**：(A) `criteria feedback-draft [--rule]` をオンデマンド口として**論理追加し MVP保留印**／(B) MVP は自動（しきい値）トリガのみ／(C) P6.2 を MVP から完全除外。
- **トレードオフ**：A＝[PR8](../methods/method-inventory.md)（フル論理＋MVP印）に従い価値経路を**論理的に塞ぐ**・実装は後。B＝しきい値運用ルールを今詰める必要が出る（[PR2](../methods/method-inventory.md) 違反）。C＝育成ループが論理的に切れる（PR6 違反）。
- **推奨 A（採用）／非推奨 B,C**：理由＝[05 台帳](../requirements/05-io-overview.md) で O-12/DS5 は MVP 最小（△）。論理経路は残し、起動はオンデマンド口で塞ぎ、自動トリガ（I-12 時間）は post-MVP（[05 ③](../requirements/05-io-overview.md)）。
- **暫定決定**：`reviewer criteria feedback-draft` を [03](03-external-interfaces.md) に追加（**MVP保留印**）。[06](06-orchestration.md) P6.2 の「オンデマンド」＝この口。
- **影響範囲**：03/06。✅ **オーナー確定**：推奨どおり「口だけ用意・実装は後（MVP保留印）」を採用。

## DD12 — lint/revert 失敗の O-14 語彙
- **論点（[spec-inspector G7](README.md)）**：`FailureStage`（intake/compose/evaluate/validate/apply）に **lint・revert の失敗段が無く**、[13 S5](../requirements/13-stabilization.md)「lint 失敗は O-14 同形式」と齟齬。
- **選択肢**：(A) `FailureStage` に `LINT` を足し、revert 対象なしは exit2（要求不正・O-14 stage 不要）／(B) revert/lint も汎用 stage に押し込む／(C) lint を O-14 でなく別形式に。
- **トレードオフ**：A＝S5 の「O-14 同形式」を満たしつつ、revert の「対象なし」は**異常でなく要求不正**として正しく分離（[03 終了コード](03-external-interfaces.md) exit2）。B＝意味の薄い stage 乱立。C＝[13 S5](../requirements/13-stabilization.md) と矛盾。
- **推奨 A（採用）／非推奨 B,C**：理由＝lint は実行前検証＝失敗は O-14（fail-close 同形式）が要件。revert 対象なしは利用者の指定ミス＝exit2 で十分。
- **暫定決定**：[01](01-class-design.md) `FailureStage.LINT` 追加。revert 対象なし＝exit2（stage 無し）。
- **影響範囲**：01/03。

---

## オーナー確定・打ち上げ事項
> **矛盾・要件欠落による停止は無し**。DD はすべて合理的デフォルトで前進。オーナー判断を仰いだ2点は**確定**：
> - ✅ **DD5（git バイナリ前提）＝採用**（オーナー確定）。`subprocess` 経由で Python 依存は増えず [Q5](../dashboard.md) を満たす（[spec-inspector G9](README.md) 健全確認済）。git 無し要件が出たら DD5-(C) へ（影響＝05 の S4 実装）。
> - ✅ **DD11（育成口は口だけ用意・実装後）＝採用**（オーナー確定）。
> - **観測（未決・運用ルール）**：[Q9](../dashboard.md) 警告の打ち上げ条件（バッチ/しきい値/dedup）は[schema](../schema/README.md) でも未決。MVP は「既出抑制（DS4）＋新規のみ即時」で前進（[05](05-persistence.md) で機構のみ）。運用ルール詰めは [PR2](../methods/method-inventory.md) によりここでは行わない。
