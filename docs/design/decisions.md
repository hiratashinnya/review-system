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
| DD17 | PF 例外の fail-close 化＝**ガードプロキシ**（オーナー決定） | アダプタ（翻訳・PF差し替え性）は残し、その前に **`GuardingPlatform`（プロキシ）** を1枚。`review()` を `StageOutcome` 返しにし try/catch→`Failure(EVALUATE)`。core は `SafePlatformPort`（例外を投げない）に依存。「PF を信用しない」責務を境界1箇所へ集約（[10]/S3・M1） | [04](04-platform-protocol.md)/adapters/core |
| DD22 | reconciliation のトークン過大消費（資産運用） | ①Step2 を docidx surgical read 化＋レイヤー限定 ②model opus→sonnet ③**検証/書込を2エージェントに分離**（`reconciliation-validator`=read-only 検証・Write/Edit なし／`reconciliation`=書込専任）。validator は構造的に本ファイルへ書けず fail-close。self_fix は validator が指示・writer が適用 | `.claude/agents/`・`tailoring-registry.md`・[CLAUDE.md](../../CLAUDE.md)・[asset-plan](../methods/asset-plan.md) |
| DD23 | spec-pipeline の非対話並列著作 fan-out をどう実装するか（Issue #62/#110・doc-system-v2 DD-22 ①-C の実装） | 新 orchestrator agent `spec-authoring-fanout` を新設し、複数親の VAL/SR/FR/NFR・SPEC 著作を `*-author` へ並列ファンアウト→`reconciliation-validator`→`reconciliation` まで sub-tree 内で完結（VALIDATION_OK は writer へ委譲・ROLLBACK/矛盾は STOP 報告）。spec-pipeline に著作 fan-out 段を明示挿入し `/io-event-ledger`（廃止）参照を除去。impl-design/asset-pipeline は単一 agent 呼びのため対象外 | `.claude/agents/spec-authoring-fanout.md`（新設）・`.claude/skills/spec-pipeline/SKILL.md` |

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

## DD18 — lateral_deploy 専用フロントマターパーサの分離（2パーサ併存）
- **論点**：`scripts/lateral_deploy.py` は自前の寛容パーサを持ち、`review_system/parsing/frontmatter.py` と2パーサが共存している。A14 観点でドリフトリスクがある（PR #13 レビュー指摘）。統一すべきか。
- **選択肢**：(A) **2パーサ併存を許容**（`lateral_deploy` は hyphenated key が必須・スタンドアロン設計）／(B) 既存パーサを hyphenated key 対応に拡張して共有／(C) 共通ライブラリとして切り出し。
- **トレードオフ**：A＝既存パーサの変更ゼロ・`lateral_deploy` のポータビリティ維持（sys.path 汚染なし設計）。B＝`review_system` 全体に波及する KEY regex 拡張が必要で Q5a の「intentional small grammar」制約と干渉。C＝MVP に過剰。
- **推奨 A（採用）／非推奨 B,C**：理由＝`KEY=[a-z_][a-z0-9_]*` は Q5a で意図的に固定した文法。SKILL.md の hyphenated key（`disable-model-invocation` 等）は `.claude/` ドメイン専用で `review_system` のパーサ拡張対象外。`lateral_deploy.py` の docstring（L22）に理由を明記済み。ドリフトは lenient/strict の役割が明確に分かれており `scripts/` 単一ファイルに閉じているため管理可能。
- **暫定決定**：2パーサ併存を許容。将来 SKILL.md フロントマターキーが `[a-z_]` 系に統一される場合は B への移行を検討。
- **影響範囲**：`scripts/lateral_deploy.py`。覆す（B 採用）なら `review_system/parsing/frontmatter.py` の KEY regex 拡張＋既存テスト更新が要る（TC-parsing-001 に波及）。→ **DD19 により superseded**（`lateral_deploy.py` 削除のためパーサ分離前提が消滅・2026-06-15）。

## DD19 — asset-lateral-deploy 変換方針変更（スクリプト廃止・エージェント手書き化）
- **論点**：`asset-lateral-deploy` スキルの変換方針を「スクリプト一括変換（`scripts/lateral_deploy.py`）」のまま続けるか。旧スクリプト方式は全サブエージェントを `.github/instructions/*.instructions.md` に量産し、GitHub Copilot の「instructions = 自動適用の常時コンテキスト」という意味を取り違えていた。加えてスクリプトは Copilot の種別（Skill / Prompt / Agent / Instructions）を「起動方式（誰がいつ呼ぶか）」で正しく振り分けられず、誤分類を生む構造的限界がある。
- **選択肢**：
  - (A) **スクリプト廃止・エージェント手書き変換**。エージェントが資産1つずつ種別を判断して変換し、対応表（Copilot ⇔ Claude Code の YAML フロントマター）を SKILL.md に記載。
  - (B) スクリプトを改修して振り分けロジックを追加。
  - (C) スクリプトを残しつつ手書き併用（二重管理）。
- **トレードオフ**：A＝機械的一括変換の構造的限界（起動方式の判断を持てず instructions 量産などの誤分類を生む）を断ち、資産単位の正確な振り分けが得られる。スクリプト・テストの保守も不要に。B＝振り分けロジックを機械で表現する複雑さが増し、それでも新種別・例外への追従が脆い。C＝スクリプトと手書きの二重管理でドリフトリスク（A14）が残る。
- **推奨 A（採用）／非推奨 B,C**：理由＝機械的一括変換は「起動方式（誰がいつ呼ぶか）」の判断を持てず、instructions 量産などの誤分類を生む。エージェントが資産1つずつ判断することで Copilot 種別への正確な振り分けが可能。
- **暫定決定（オーナー直接承認・確定）**：A 採用。`scripts/lateral_deploy.py` とそのテストを削除し、`asset-lateral-deploy` は SKILL.md の方針・対応表に基づくエージェント手書き変換に全面移行（2026-06-15 オーナー承認）。
- **影響範囲**：
  - `scripts/lateral_deploy.py` → **削除済み**。
  - `tests/unit/test_lateral_deploy.py` → **削除済み**（テスト 137 → 109 件）。
  - `.claude/skills/asset-lateral-deploy/SKILL.md` → 方針・対応表（Copilot ⇔ Claude Code の YAML フロントマター）に全面改定済み。
  - **DD18 との関係**：DD18 は `lateral_deploy.py` の2パーサ併存を許容した決定だが、スクリプト削除により前提（スクリプトの存在）が消失。**DD18 は本決定（DD19）により superseded（無効化）**。DD18 本文に `→ DD19 により superseded` を追記する（reconciliation で反映）。
  - `docs/dashboard.md` → DD18 参照行に DD19 の決定を追記し、DD18 参照を更新する（reconciliation で反映）。
  - 義務辺（決定スパイン）：本決定は起票時点で全面反映済みのため、未反映を表す義務辺 `DD19→X` は持たない。

### DD18 への参照
→ DD18（`lateral_deploy.py` 2パーサ併存許容）は本決定（DD19）により superseded。`lateral_deploy.py` が削除されたため、2パーサ併存という前提自体が消滅した。

## DD22 — reconciliation のトークン過大消費（資産運用）
- **論点**：`reconciliation` エージェントが usage 上で突出してトークンを消費している。原因は `.claude/agents/reconciliation.md` の Step2「合成グラフ構築」が `doc-system/` 配下（約15,500行・`02-what/03-spec.md` だけで 5,119行）を**丸読み**していたこと、機械的検証＋書込を `model: opus` で実行していたこと、検証/書込を1エージェントで抱えていたこと。
- **選択肢**：
  - **A（surgical read）**：Step2 を tmp 参照 ID＋親＋backref 対象のみ `python3 -m docidx show/deps/dependents` で個別取得に変更。レイヤーで読込範囲も限定。
  - **B（モデル降格）**：`model: opus → sonnet`（処理は Bloom Apply 相当）。
  - **C（検証/書込分離）**：`reconciliation-validator`（read-only 検証・Write/Edit なし）と `reconciliation`（書込専任）に分離。
  - **D（内部ステップ分割のみ）**：同一エージェント内で検証/書込ステップを整理（C の代替）。
- **トレードオフ**：A＝読込 15,500行→数十〜数百行。B＝コスト削減・検証は機械的なので品質劣化リスク小。C＝validator は Write/Edit を構造的に持たず、バグ/誤判定でも本ファイルへ書けない **fail-close** を得る（orchestration の fail-close 思想に整合）。D＝エージェント濫造を避けるが Write/Edit を保持するため構造保証は得られない。
- **推奨 A＋B＋C（採用）／非推奨 D**：理由＝C の付加価値（ツール権限による構造的 fail-close）は D では得られず、asset-auditor 点検でも「validator は Write を外すことで一段深い防御になる」と確認。C 採用に伴い ①self_fix は validator が確定値つき指示として返し writer が適用（validator は書けないため）②reconciliation は検証ロジックを持たない writer 専任へ縮約（二重実装ドリフト防止）。
- **暫定決定（オーナー確認のうえ採用）**：A＋B＋C を実装。validator=`reconciliation-validator`（model: sonnet・Read/Grep/Glob/Bash〔docidx 専用〕）、writer=`reconciliation`（model: sonnet・Write/Edit 保持）。2段パイプライン `*-author`→validator→（VALIDATION_OK なら）reconciliation。ROLLBACK 時は writer を呼ばず著作エージェント再起動。
- **影響範囲**：
  - `.claude/agents/reconciliation.md`（writer 専任へ縮約）・`.claude/agents/reconciliation-validator.md`（新設）。
  - `.claude/tailoring-registry.md`（validator 行追加・reconciliation 行更新）。
  - `CLAUDE.md`（サブエージェント一覧・ノード著作の委譲ルールを2段化）。
  - `docs/methods/asset-plan.md`（agents ツリー同期）。
  - 覆す（validator を廃し1エージェントへ戻す）場合：上記4ファイルの記述と委譲フローを再統合。
  - 義務辺：本決定は資産運用（`.claude/`）への反映で、in-graph 義務辺は持たない。

## DD23 — spec-pipeline の非対話並列著作 fan-out（Issue #62/#110・doc-system-v2 DD-22 ①-C の実装）
- **論点**：doc-system-v2 の **DD-22（①-C ハイブリッド）** は「対話入口は skill・**非対話 fan-out のみ orchestrator agent 化**」を決めたが、対象 pipeline skill（spec/impl-design/asset）には**そもそも並列 fan-out する著作ロジックが存在しなかった**。要求層ノード著作（`requirements-author`/`spec-author` の呼び出し）は主文脈で場当たりに行われ、skill に成文化されていない。オーナー指示「そもそも並列呼び出しになってないことがおかしいからそこから直す」（2026-07-06）に従い、**まず並列著作の実体を作る**。
  - 派生論点3つ：(a) エージェントはエージェントを spawn できるのか（旧 skill コメントは「呼べない」と明記）／(b) 著作段を pipeline のどこに挿すか／(c) 3 pipeline すべてに専用 orchestrator を作るのか、spec-pipeline だけか。
- **選択肢**：
  - **A（新 orchestrator agent `spec-authoring-fanout` を新設・採用）**：spec-pipeline が「著作すべき親ノード群」を確定した段で、複数親の VAL/SR/FR/NFR（`requirements-author`）・SPEC（`spec-author`）を**1メッセージ内で並列 Task 発行**し、まとめて `reconciliation-validator`→（VALIDATION_OK なら）`reconciliation` へ委譲。ROLLBACK/矛盾は STOP 報告。
  - **B（skill 内で主文脈が逐次に author を呼ぶ現状維持）**：並列化されず context 隔離も得られない（＝オーナー指摘の「並列になってない」を放置）。
  - **C（3 pipeline 全部に専用 orchestrator agent を作る）**：impl-design/asset の非対話部は**単一 agent 呼び**（それぞれ spec-inspector 1回・asset-auditor 1回）で、並列化する複数ノードが無い＝専用 orchestrator は空箱になる。
- **派生論点の解決**：
  - **(a) エージェントは子エージェントを spawn 可能**。根拠＝**DD-22 本文**（doc-system-v2・decided 2026-07-01）が公式ドキュメントで確認済みと明記：**Claude Code v2.1.172 以降サブエージェントが子サブエージェントを spawn 可能／main 直下から数え depth 5 が最終段（further spawn 不可）・上限固定**。本 orchestrator（depth 1）→ `*-author`/validator/reconciliation（depth 2）は depth 5 に収まる。旧 pipeline skill の「サブエージェントはサブエージェントを呼べないため skill にする」は DD-22 で無効化済み（skill に残す理由は**ネスト不可**ではなく**対話性**）。
  - **(b) 挿入位置**＝台帳（手順2）＋ structured-analysis（手順4）が「何を著作するか」を出した**直後**（手順5）。align のパラメータ確定・spec-inspector の矛盾停止・mvp-scope の価値線引き（対話段）は skill に残す（DD-22 ①-C）。
  - **(c) spec-pipeline だけ**に作る。impl-design/asset は単一 agent 呼びで並列化余地が無い（C の空箱回避）。
  - **VALIDATION_OK の扱い＝writer へ委譲（report-back でなく）**：非対話 fan-out の趣旨に沿い、著作→検証→**書込（reconciliation）まで sub-tree 内で完結**させ、主文脈にはコンパクト要約（`FANOUT_DONE`）だけ返す（context 隔離を最大化）。既存パイプラインも主文脈から author→validator→reconciliation を回しており、VALIDATION_OK 後の決定的書込は据え置き。**矛盾・ROLLBACK・曖昧は書込前に STOP**（AskUserQuestion 不可のため skill が Q/DD 起票→オーナー）。
- **推奨 A（採用）／非推奨 B,C**：理由＝A はオーナー指摘の「並列になってない」を実体化し DD-22 ①-C の非対話 fan-out を具現。B は放置、C は空箱で asset 濫造（A14 に反する）。
- **暫定決定**：
  - `.claude/agents/spec-authoring-fanout.md` を新設（`model: sonnet`＝コーディネータ／判断困難は STOP の fail-safe・実質著作は opus の `*-author` に委譲・Bloom は Apply〜Evaluate 相当だが routing/thoroughness-bound）。`tools: Task, Read, Grep, Glob, Bash`（Task＝子エージェント spawn・Write/Edit は持たない＝著作/書込しない責務境界）。description で「単一ノード著作でない・validator でない・writer でない」を明記し `*-author`/`reconciliation` との auto-dispatch 衝突を回避。
  - `.claude/skills/spec-pipeline/SKILL.md` を改訂：(1) 廃止済み `/io-event-ledger` 参照を「台帳＋イベントリスト→analysis-author 著作（2段確定）」へ差し替え（tailoring-registry 2026-06-11 の移管を反映）、(2) 手順5 に著作 fan-out 段を明示挿入、(3) ハイブリッド分担（対話＝skill／非対話 fan-out＝agent）を冒頭に明記、(4) 旧コメント「サブエージェントは呼べない」を DD-22 の depth-5 事実で更新。
- **影響範囲**：`.claude/agents/spec-authoring-fanout.md`（新設）・`.claude/skills/spec-pipeline/SKILL.md`（改訂）。impl-design-pipeline/asset-pipeline は**不変**（単一 agent 呼びで並列化余地なし＝監査で確認）。in-graph 義務辺は持たない（`.claude/` 資産運用への反映）。**覆す場合**＝`spec-authoring-fanout` を撤去し spec-pipeline の著作段を主文脈逐次呼びへ戻す（影響は当該2ファイルに閉じる）。
  - **未確定リスク（要フォロー）**：本エージェントの並列 fan-out・深さ 2 ネストは**実 e2e 未実行**（本タスクはプロンプト/エージェント定義の著作）。実運用で depth/並列 Task の挙動を確認し、齟齬があれば FND 起票する。

---

## オーナー確定・打ち上げ事項
> **矛盾・要件欠落による停止は無し**。DD はすべて合理的デフォルトで前進。オーナー判断を仰いだ2点は**確定**：
> - ✅ **DD5（git バイナリ前提）＝採用**（オーナー確定）。`subprocess` 経由で Python 依存は増えず [Q5](../dashboard.md) を満たす（[spec-inspector G9](README.md) 健全確認済）。git 無し要件が出たら DD5-(C) へ（影響＝05 の S4 実装）。
> - ✅ **DD11（育成口は口だけ用意・実装後）＝採用**（オーナー確定）。
> - **観測（未決・運用ルール）**：[Q9](../dashboard.md) 警告の打ち上げ条件（バッチ/しきい値/dedup）は[schema](../schema/README.md) でも未決。MVP は「既出抑制（DS4）＋新規のみ即時」で前進（[05](05-persistence.md) で機構のみ）。運用ルール詰めは [PR2](../methods/method-inventory.md) によりここでは行わない。
