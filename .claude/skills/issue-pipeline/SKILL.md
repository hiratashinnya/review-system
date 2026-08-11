---
name: issue-pipeline
description: Orchestrate a batch of open GitHub Issues through implement→PR→review→merge→close, one Issue at a time. The main thread stays thin — it triages processing order, dispatches issue-implementer / pr-reviewer sub-agents (model tier via bloom-model-tier, risk-based reviewer model), exchanges decisions with the owner via AskUserQuestion (showing premises/tradeoffs first), and tracks progress. Run only when explicitly invoked. NOT for authoring doc-system-v2 nodes (use spec-pipeline / impl-design-pipeline).
disable-model-invocation: true
---

# Issue 処理パイプライン（implement → PR → review → merge → close の連続処理）

> 複数のオープン Issue を **1件ずつ完結**させる repo 運用オーケストレータ。主文脈（このスキルの呼び出し元）は
> **よほど軽微でない限り自分で実装せず**、タスク管理・進捗報告・オーナーとの意思決定に専念する（Issue #120 ③）。
> ファンアウト実行は `issue-implementer`（実装→PR）と `pr-reviewer`（レビュー→マージ）へ委譲し、
> 重い調査は `agy-delegate` を積極利用する。
> 原則：[spec-principles](../spec-principles/SKILL.md)（PR7 空で止めない・PR8 消さない）／規約：[CLAUDE.md](../../../CLAUDE.md)
> （スコープ拡大禁止・スケジュール独断禁止・AI-attribution・Bloom 委譲）。**このスキルはそれらを再掲せず、上に立って回す**。

## 役割分担（DD-22 の対話／非対話境界を厳守）
- **主文脈＝対話オーナー**：`AskUserQuestion` を持つのはここだけ。**順序決め・オーナー判断・先送り可否・スコープ拡張の起票判断**を担う。
- **`issue-implementer` / `pr-reviewer`＝非対話ファンアウト**：`AskUserQuestion` を持たない。曖昧・矛盾に当たったら**STOP して報告**（意見なき停止禁止＝原案＋比較＋推奨を添えて返す）。
  対話ロジックを非対話エージェントに埋め込まない／順序・オーナー判断を主文脈から外へ出さない（DD-22）。
- **権限境界はハーネスで機械強制**（`.claude/hooks/agent-command-gate.sh`・PreToolUse）：`issue-implementer` は push/PR 可・merge 不可、
  `pr-reviewer` は merge 可・push 不可。プロンプトの自制ではなく機械ゲート（既知の限界は Issue #129・多層防御の一枚）。

## 段（各 Issue を直列に回す。バッチ内 Issue は ① で順序確定）

### ① 処置順の原案 → オーナー承認（主文脈・対話）
オープン Issue 一覧から**推奨処置順**を立てる（Issue #120 ①）。
1. `gh issue list` で対象を確定。各 Issue の本文・相互参照（"depends on #N" / "blocked by" / 同一ファイル群を触る等）を読む。
   - **読み取りが重いバッチ（多数 Issue・横断調査が要る）なら read-only 委譲でコンテキストを節約**：一般調査は `general-purpose`/`Explore`、
     大規模な横断影響調査は `agy-delegate`（疎通 OK 時）へ。**ただし「推奨順」を決めるのは主文脈**（対話オーナーが即 AskUserQuestion できるため・DD-22）。
     専用 `issue-triage` エージェントは作らない（generic な issue 読解で asset-auditor も新規不要と判定・A14 再利用優先／決定は対話側に残す）。
2. 依存を有向グラフ化し、**順序必須（前段の成果に依存）**と**並列可（独立）**を分離。ブロッカーを先に、葉を後に。
3. **原案＋根拠＋メリデメを必ずチャットに提示してから** `AskUserQuestion` で承認/修正を仰ぐ（Issue #120 ③・空で止めない）。
   提示物＝依存グラフ要約・推奨順・並列可否・各 Issue のリスク見立て（② のレビュー model 選定に使う）。

### ② 1 Issue を完結（承認された順に直列。前 Issue が merge & close 済みになってから次へ・Issue #120 ②）
各 Issue につき次を回す。**主文脈は dispatch と進捗記録に専念し、実装・レビューはしない**。

**②-a 実装（`issue-implementer` へ委譲）**
- **dispatch の直前に managed Issue-start gate を通す（`issue-start-gate`・`.claude/hooks/issue-start-gate.sh`・PreToolUse）。**
  この hook は `issue-implementer` への `Task`/`Agent` dispatch の `tool_input.prompt` に、次の機械可読行を
  **ちょうど1つ**含めることを要求する（契約の実体＝`issue_start/gate.py` の `_claude_request`・
  `issue_start/managed-entrypoints-v1.json` の `claude` transport）：
  ```
  ISSUE_START_BINDING_V1={"entrypoint":"issue-pipeline","repository":"OWNER/REPO","issue":N,"branch_name":"BRANCH","base_ref":"DEFAULT","base_oid":"40-HEX","base_pr":null}
  ```
  - `entrypoint`：この managed entrypoint では常に文字列リテラル `"issue-pipeline"`
    （`managed-entrypoints-v1.json` の登録値と exact 一致が必須）。
  - `repository`：`git remote get-url origin` を `OWNER/REPO` の canonical 形へ変換した値
    （HTTPS/SSH いずれも可・`gate.py` の `_canonical_github_repository` と同じ正規化）。
  - `issue`：dispatch 対象の Issue 番号（1以上の整数。文字列不可）。
  - `branch_name`/`base_ref`/`base_oid`：後続で実装者に渡す
    `python3 -m gitgate new-branch <name> --repository OWNER/REPO --base-ref DEFAULT --base-oid OID [--base-pr N]`
    と**同じ値**（fresh fetch 済み `origin/<default>` の exact 40 桁 OID）。marker 内のこれらの値は
    branch-source ALLOW の根拠には**ならない**——`gitgate new-branch` が別途 fresh に再検証する
    （`docs/tools/issue-start-and-branch-source.md`「決定」節）。
  - `base_pr`：stacked branch でなければ `null`。stacked のときだけ same-repository の OPEN PR 番号（整数）。
  - **exact 7 field 以外の混在・fieldの欠如は拒否される**（`set(raw) != {entrypoint, repository, issue,
    branch_name, base_ref, base_oid, base_pr}` で `ISSUE_START_BINDING_UNKNOWN_FIELD`）。
  marker が**存在しない・prompt 中に複数行ある**場合は `ISSUE_START_BINDING_MISSING_OR_DUPLICATE` で
  hook が dispatch そのものを deny する（`issue-implementer` は起動されない）。値の型・形式不正
  （`base_oid` が40桁hexでない等）はそれぞれ専用の reason code（`ISSUE_START_BRANCH_INVALID`／
  `ISSUE_START_BASE_REF_INVALID`／`ISSUE_START_BASE_OID_INVALID`／`ISSUE_START_BASE_PR_INVALID`等）で
  fail-close する。別経路への迂回はできない。
- **model/effort は [bloom-model-tier](../bloom-model-tier/SKILL.md) のルーブリックで決める**（Issue #120 ④）。実装は既定 `sonnet`。
  Bloom Lv6・判断ボトルネック（曖昧仕様からの新規構造化・不可逆な設計判断を含む Issue）なら `model: opus` override で dispatch。
- dispatch prompt には**タスク固有情報のみ**（Issue 番号・関連ノード ID・スコープ）＋**共通契約への参照**（下記「共通指示の配り方」）。
- **`handoff_path` を主文脈が絶対パスで渡す**（worktree 曖昧性の除去）：`<main-worktree>/tmp/_handoff/issue-implementer--issue-<N>.yaml`。
  `<main-worktree>` は主文脈の作業ルート（`git rev-parse --show-toplevel` で確定。主文脈は linked worktree ではなくメイン側で回す）。
  implementer が `.worktrees/<name>/` を cwd にすると相対 `tmp/_handoff/...` はその worktree 配下へ解決され、主文脈から回収できない——
  **書き先は主文脈が決めて絶対パスで渡し、implementer はそのパスへそのまま書く**。渡し忘れたら implementer は STOP する契約（`issue-implementer.md`「入力」）。
- 戻り＝`HANDOFF: <渡した handoff_path>` ＋1行要約。**PR URL・変更ファイル一覧・テスト結果・スコープ外指摘は主文脈で当該ファイル（自分が渡した絶対パス）を Read して取る**（1行要約だけで判断しない）。**`status: stop`（曖昧・矛盾）なら `stop_reason` ごと主文脈で受けてオーナーへ**（PR7）。

**②-b 初回レビュー（`pr-reviewer` へ委譲・model はリスクで選ぶ）**
- **初回レビューの model はリスク/難易度で選ぶ**（Issue #120 ④）。レビュー＝Bloom Lv5 評価。下の**リスク信号表**で `sonnet` / `opus` を機械的に引く
  （「判断で」で済ませない）。既定 override なし＝`sonnet`、opus 該当時のみ `model: opus` で dispatch。
- **指摘の処置要否・処置担当モデル（Sonnet 降格可否）は `pr-reviewer` 自身が決める**（Issue #120 ④・主文脈は決めない）。
  レビューアが「指摘は明確・機械的 → Sonnet で処置」と判断したら、主文脈はその指示どおり ②-c を回すだけ（降格判断を横取りしない）。
- **レビュー指摘・処置結果は PR レビューコメントに残す**（Issue #120 ⑥・Claude Code(AI) 明記＋具体的な変更/根拠。`gh pr comment`。
  承認/却下ステータスを偽らない＝`pr-reviewer.md` の絶対規範）。

**②-c 是正 → 再レビュー（指摘があった場合のループ）**
- **是正は `issue-fixer` へ差し戻す**（`issue-implementer` ではない＝Issue #308。`pr-reviewer` は push 不可＝コードを書けない）。
  `issue-implementer` は**初回実装専任**で、是正依頼を受けたら STOP する契約になっている。担当 model は
  **②-b でレビューアが決めた降格判断に従う**（明確な指摘なら `sonnet`）。
- **レビュー結果を先にカルテへ取り込む**（`issue-fixer` を dispatch する前）。`pr-reviewer` は構造化 finding
  （`### F-<issue>-<seq>` ブロック＋`harm`/`harm_detail`/`severity`/`locus`/`summary`/`evidence`/`expected`/`recheck`/`status`）を
  返すので、主文脈がそれをファイルへ書き出して取り込む：
  `python3 -m karte ingest-review --issue <N> --round <R> --from <path>`
  **`--from` に渡すレポートは repo-root 配下（例 `tmp/` 配下）へ書き出す**——`karte` は `resolve_within_repo` で
  リポジトリ外のパスを fail-close で拒否するため、スクラッチパッド等へ書くと取り込みが失敗する
  （`tmp/` は gitignore 済みでコーパスを汚さない）。
  （ID の採番・再発番検出・前ラウンド未解消 finding の全件再掲チェックはこの CLI が fail-close で行う）。
  **`ingest-review` は主文脈が実行する**——是正当事者である `issue-fixer` には権限ゲートで許可されていない
  （自分の指摘を `resolved` にできてしまうため・Issue #341 F-341-04）。
- **`karte_path` と `round` を主文脈が絶対パスで渡す**（`handoff_path` と同じ理由＝worktree 曖昧性の除去）：
  `<main-worktree>/tmp/_karte/issue-<N>.md`。渡し忘れたら `issue-fixer` は STOP する契約（`issue-fixer.md`「入力」）。
  進行ポインタ `tmp/_karte/active.json` は `ingest-review` が更新する。
- `issue-fixer` は**診断してから直す**（`karte render` で前ラウンドの試行・転換指令・未解消 finding の
  `expected`/`recheck` を引き、`karte append` で診断を登録してからコードを触る）。同じアプローチの3件目は
  `append` が機械的に拒否する＝**ラウンド上限ではなく類似で切る**。
- **再レビューは常に Sonnet**（Issue #120 ⑤・`pr-reviewer` を override なし＝既定 `sonnet` で dispatch）。
- clean になるまで ②-c を繰り返す。**握りつぶし禁止**：対応不要に見えても FND/Q 起票を主文脈へ提案させ、据え置きはオーナー判断（下記 ③・④）。

> **未了（Issue #310）**：続行/停止の判定に使う**「実害」の定義**と**エスカレーション条件**（`karte status` の
> 結果をどう読んで打ち上げるか）は #310 で本節に追記する。本 PR（#341）は **#308 で新設した `issue-fixer` が
> どこからも呼ばれない状態を作らないための最小配線**に留めており、ループの停止条件は従来どおり
> 「clean になるまで」＋「握りつぶし禁止」で運用する。

**②-d マージ → クローズ → 次へ**
- `pr-reviewer` が genuinely clean と判断したら `gh pr merge`（マージは reviewer 専権・機械ゲート）。
- `Closes #N` で自動クローズされなければ主文脈がクローズ（クローズは主文脈がしてよい）。**merge & close を確認してから次 Issue へ**（Issue #120 ②）。

### ③ スコープ拡張は別 Issue に逃がす（PR 肥大化の抑制・Issue #120 ⑧）
レビュー/調査中に**現 PR/Issue のスコープを超える対応**が要ると分かったら、現 PR で直さず **サブ Issue / 別 Issue を起票**（`gh issue create`）。
- `issue-implementer`/`pr-reviewer` は「スコープ外指摘」を報告して STOP する（自分で直さない・CLAUDE.md スコープ拡大禁止）。**起票の実行は主文脈**。
- doc-system-v2 に関わる指摘なら FND/Q ノード起票（`verification-author` 経由）も併せて主文脈が判断（CLAUDE.md）。

### ④ 先送りは必ずオーナー許可（独断禁止・Issue #120 ⑨ / CLAUDE.md スケジュール独断禁止）
指摘・対応を先送り/繰り越すときは、**背景・検討結果・メリデメを提示した上で `AskUserQuestion` で許可を取る**。
- **AI が単独で「対応不要」「後でよい」「次スプリント繰り越し」と結論づけない**（CLAUDE.md・過去インシデント）。
- `scheduled` は空のまま「今実施 vs 繰り越し＋推奨」を添えて委ねる。判断者と理由をコメント/ノードに明記。

## リスク信号表（②-b 初回レビュー model 選定・bloom-model-tier の軸2を Issue レビューに具体化）
レビュー＝Bloom Lv5 評価。**判断ボトルネック側の信号が1つでも強く立てば `opus`、すべて網羅性側なら `sonnet`（+high effort）**。

| 信号 | Sonnet 寄り（網羅性ボトルネック） | Opus 寄り（判断ボトルネック） |
|---|---|---|
| ブラストレディアス | 局所（1〜数ファイル・限定モジュール） | コーパス横断・共有資産・多数ノードの ref_version 伝搬 |
| 変更規模 | 小（数十行・定型追加） | 大（構造改変・広域リファクタ） |
| パターンの新規性 | 既存パターン踏襲（テンプレ流し込み・既存に倣う） | 前例なし・新規構造の創出・設計判断を含む |
| 触る対象の性質 | プローズ/資産テキスト・ドキュメント | 権限ゲート/フック/セキュリティ境界・doc-system グラフ構造・型 |
| 可逆性 | 容易に差し戻せる | 不可逆・広範囲に波及 |
| 仕様の明確さ | 受け入れ基準が一意 | 曖昧・利害 trade-off・解釈の余地 |

- 迷ったら **opus 側に倒す**（bloom-model-tier のタイブレーク＝effort は品質の代理変数にすぎない・安全側）。選定根拠を1行残す（信号→model）。
- **レートリミット／セッション上限は選定根拠にしない**（CLAUDE.md「レートリミット由来の品質降格の禁止」・Issue #321）。
  サブエージェントが上限で停止しても、上表の信号は変わらない。停止＝主文脈が動いている＝枠は回復している。
  同じ model・effort・委譲構成でそのまま再投入する（降格・effort 低下・主文脈代行はしない）。
  **上限停止後の再投入は②-cの「再レビュー」ではなく初回レビューの継続**であり、次項の
  「再レビューは常に Sonnet」は適用しない（対象は同じ model・上表で選定した model のまま再投入する）。
- **再レビューは表に依らず常に Sonnet**（Issue #120 ⑤）。是正の担当 model は**レビューアの降格判断に従う**（主文脈が決めない・Issue #120 ④）。

## 共通指示の配り方（dispatch テンプレをリーンに保つ）
`issue-implementer`/`pr-reviewer` の**恒常的な共通契約**（決定点で前提/背景/メリデメ＋選択肢＋推奨を報告に添える・PR コメントは AI 明記＋具体・
曖昧は STOP 報告・スコープ外は起票提案）は、**各エージェントの system prompt（`.claude/agents/*.md`）に常設**する（読者が見る場所・版管理・毎回自動適用）。
- **dispatch prompt には毎回タスク固有情報だけ**を書く。バッチ共通の補足がある場合のみ、CLAUDE.md の規約どおり
  `tmp/<sprint>/issue-pipeline-common.md` に書き出して各 dispatch から参照させる（同一指示をコンテキストに展開しない）。
- **SubagentStart フックは採らない（設計判断）**：`SubagentStart`（`hookSpecificOutput.additionalContext` で子コンテキストへ注入可）は実在するが、
  本パイプラインでは採用しない。理由＝(1) 対象2エージェントは本パイプライン専用で、恒常契約は各 `.md` に置く方が可視・版管理でき常に効く（フックだと settings.json ＋シェルに分散）。
  (2) 本 repo でフックは**機械的に拒否できる境界**（push/merge ゲート＝agent-command-gate）に限定する慣行（PR2・機械判定と運用ルールを混ぜない）。ただし Bash 文字列の静的検査であり、非バイパスの完全防御とは扱わない。
  助言的指示の配布はその範疇でない。(3) 常時 ON のグローバル副作用は、明示ブロックに比べ保守面が重く不透明で、得られるトークン節約は限定的。

## 重い作業は agy を積極利用（Issue #120 ⑦・fail-close）
横断影響調査・参照/孤児調査・スクラッチ計算・並列サブクエリなどの**重い調査**は `agy-delegate` へ回す。
- `agy-delegate` は**移譲前に必ず疎通チェック**（`antigravity_status`）し、NG（クラウド/ヘッドレス等）なら**移譲せず主文脈が直接遂行にフォールバック**（fail-close）。
- **正本への書き込み・確定著作・無検証コード採用は移譲しない**（agy 産は素案/レポート＝入力にすぎない・`agy-delegate.md` のガバナンス境界）。

## 点検観点（done）
- ① 推奨順を依存グラフ＋根拠付きで提示し、`AskUserQuestion` でオーナー承認を得た（独断で処理を始めていない）。
- 各 Issue が **implement→PR→review→merge→close** を1件ずつ完結（前 Issue の close 確認後に次へ）。
- 実装 model は bloom-model-tier、初回レビュー model はリスク信号表で選定し**根拠を1行残した**。是正降格は**レビューアが決めた**。**再レビューは Sonnet**。
- レビュー指摘・処置結果が **PR レビューコメント**に AI 明記＋具体で残っている（Issue #120 ⑥）。
- スコープ拡張は**別 Issue に逃がした**（現 PR を肥大化させていない・⑧）。
- 先送りは**オーナー許可を取った**（AI 独断で「対応不要/繰り越し」していない・⑨）。
- 主文脈は実装/レビューを自分でやらず、タスク管理・進捗報告・意思決定に専念した（③）。

## 成果物
- 承認済み処置順 ＋ 各 Issue の PR（merge/close 済み）＋ PR レビューコメント（AI 明記）＋ 起票したサブ Issue/FND/Q（あれば）＋ 進捗ログ。
