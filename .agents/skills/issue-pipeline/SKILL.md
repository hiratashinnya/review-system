---
name: issue-pipeline
description: 複数のオープン GitHub Issue を実装→PR→レビュー→マージ→クローズで1件ずつ処理するオーケストレータ。処置順の確定、issue-implementer/pr-reviewer サブエージェントへの委譲（model は bloom-model-tier、レビュー model はリスクベース）、オーナーとの意思決定、進捗管理を扱う。ユーザーが明示的に起動した場合のみ使う。doc-system-v2 ノード著作には使わない（spec-pipeline / impl-design-pipeline を使う）。
---

すべての説明・報告・質問は日本語で行う。ユーザーが明示的に別言語を指定した場合を除き、この skill の応答も日本語に統一する。

# Issue 処理パイプライン（implement → PR → review → merge → close の連続処理）

> 複数のオープン Issue を **1件ずつ完結**させる repo 運用オーケストレータ。主文脈（このスキルの呼び出し元）は
> **よほど軽微でない限り自分で実装せず**、タスク管理・進捗報告・オーナーとの意思決定に専念する（Issue #120 ③）。
> ファンアウト実行は `issue-implementer`（`.codex/agents/issue-implementer.toml`・実装→PR）と `pr-reviewer`（`.codex/agents/pr-reviewer.toml`・レビュー→マージ）へ委譲し、
> 重い調査は `agy-delegate`（`.codex/agents/agy-delegate.toml`）を積極利用する。
> 原則：[spec-principles](../spec-principles/SKILL.md)（PR7 空で止めない・PR8 消さない）／規約：[AGENTS.md](../../../AGENTS.md)
> （スコープ拡大禁止・スケジュール独断禁止・AI-attribution・Bloom 委譲）。**このスキルはそれらを再掲せず、上に立って回す**。

## 役割分担（DD-22 の対話／非対話境界を厳守）
- **主文脈＝対話オーナー**：ユーザーと直接対話できるのはここだけ（Codex CLI のメインスレッド）。**順序決め・オーナー判断・先送り可否・スコープ拡張の起票判断**を担う。
- **`issue-implementer` / `pr-reviewer`＝非対話ファンアウト**：ユーザーへ直接質問しない。曖昧・矛盾に当たったら**STOP して報告**（意見なき停止禁止＝原案＋比較＋推奨を添えて返す）。
  対話ロジックを非対話エージェントに埋め込まない／順序・オーナー判断を主文脈から外へ出さない（DD-22）。
- **権限境界は Codex hook とプロンプト規律の両方で遵守する**（`.codex/agents/issue-implementer.toml`／`pr-reviewer.toml` の `developer_instructions`、`.codex/hooks/agent-command-gate.sh`）：`issue-implementer` は push/PR 可・merge 不可、
  `pr-reviewer` は merge 可・push 不可。Codex hook は PreToolUse の静的検査であり完全な sandbox ではないため、禁止操作はプロンプト規律としても厳守する（既知の限界は Issue #129/#181・多層防御の一枚）。Claude Code 側の `.claude/hooks/agent-command-gate.sh` と同等の境界を目指すが、クライアント差分と trust 状態の限界を過信しない。

## 段（各 Issue を直列に回す。バッチ内 Issue は ① で順序確定）

### ① 処置順の原案 → オーナー承認（主文脈・対話）
オープン Issue 一覧から**推奨処置順**を立てる（Issue #120 ①）。
1. `gh issue list` で対象を確定。各 Issue の本文・相互参照（"depends on #N" / "blocked by" / 同一ファイル群を触る等）を読む。
   - **読み取りが重いバッチ（多数 Issue・横断調査が要る）なら read-only 委譲でコンテキストを節約**：一般調査は Codex の汎用 read-only subagent、
     大規模な横断影響調査は `agy-delegate`（疎通 OK 時）へ。**ただし「推奨順」を決めるのは主文脈**（対話オーナーが即座に質問できるため・DD-22）。
     専用 `issue-triage` エージェントは作らない（generic な issue 読解で asset-auditor も新規不要と判定・A14 再利用優先／決定は対話側に残す）。
2. 依存を有向グラフ化し、**順序必須（前段の成果に依存）**と**並列可（独立）**を分離。ブロッカーを先に、葉を後に。
3. **原案＋根拠＋メリデメを必ずチャットに提示してから**日本語で承認/修正を仰ぐ（Issue #120 ③・空で止めない）。
   提示物＝依存グラフ要約・推奨順・並列可否・各 Issue のリスク見立て（② のレビュー model 選定に使う）。

### ② 1 Issue を完結（承認された順に直列。前 Issue が merge & close 済みになってから次へ・Issue #120 ②）
各 Issue につき次を回す。**主文脈は dispatch と進捗記録に専念し、実装・レビューはしない**。

**②-a 実装（`issue-implementer` へ委譲）**
- **model/effort は [bloom-model-tier](../bloom-model-tier/SKILL.md) のルーブリックで決める**（Issue #120 ④）。実装は既定モデル・既定 effort。
  Bloom Lv6・判断ボトルネック（曖昧仕様からの新規構造化・不可逆な設計判断を含む Issue）なら `model_reasoning_effort = "xhigh"` override で dispatch。
- dispatch prompt には**タスク固有情報のみ**（Issue 番号・関連ノード ID・スコープ）＋**共通契約への参照**（下記「共通指示の配り方」）。
- 戻り＝PR URL・変更ファイル一覧・テスト結果・スコープ外指摘。**STOP 報告（曖昧・矛盾）なら主文脈で受けてオーナーへ**（PR7）。

**②-b 初回レビュー（`pr-reviewer` へ委譲・model はリスクで選ぶ）**
- **初回レビューの model/effort はリスク/難易度で選ぶ**（Issue #120 ④）。レビュー＝Bloom Lv5 評価。下の**リスク信号表**で `model_reasoning_effort` の
  `high` / `xhigh` を機械的に引く（「判断で」で済ませない）。既定 override なし＝`high`、判断ボトルネック該当時のみ `model_reasoning_effort = "xhigh"` で dispatch。
- **指摘の処置要否・処置担当 agent / model_reasoning_effort（降格可否）は `pr-reviewer` 自身が決める**（Issue #120 ④・主文脈は決めない）。
  レビューアが「指摘は明確・機械的 → 既定 effort で処置」と判断したら、主文脈はその指示どおり ②-c を回すだけ（降格判断を横取りしない）。
- **レビュー指摘・処置結果は PR レビューコメントに残す**（Issue #120 ⑥・Codex CLI (AI) 明記＋具体的な変更/根拠。`gh pr comment`。
  承認/却下ステータスを偽らない＝`pr-reviewer.toml` の絶対規範）。

**②-b-2 Claude review MCP による別視点レビュー（条件付き・merge 前）**
- Codex `pr-reviewer` の初回レビュー後、merge 前に下の**Claude レビュー起動条件表**で追加レビュー要否を判定する。Claude は判断の置き換えではなく、別モデル視点のリスク探索入力として扱う。
- **必須条件に該当する PR は merge 前に `claude_review` MCP を呼ぶ**。Claude が rate limit 等で使えない場合は STOP し、待つ/今回は Codex レビューのみで進める/スコープを分割する、の選択肢と推奨をオーナーへ提示する。
- **任意条件のみなら、コスト・待ち時間・レビュー価値を1行で見積もって呼ぶ/省くを記録する**。省く場合も「なぜ省いたか」を進捗ログまたは PR コメントに残す。
- `pr_number` を指定して GitHub 文脈は MCP に取得させる。prompt にはタスク固有の観点だけを書く。恒常指示は `.codex/mcp/claude_review/common_instructions.md` が MCP により自動注入されるため、dispatch prompt に展開しない。
- 既定は `model: opus`。`fable` はドキュメント/プロンプト/運用文言/ユーザー向け説明の読み味や曖昧さを別視点で見たい場合、または Opus/Codex の見解が割れて表現・方針面の第三視点が必要な場合に追加で使う。コード正当性・セキュリティ境界・merge 可否の最終補助は Opus を優先する。
- Claude の所見は PR コメントへ **Codex AI agent** 由来として要約し、採否は Codex `pr-reviewer` または是正後の再レビュー文脈で確認する。Claude の所見を未検証のまま merge 判定に直結しない。

**②-c 是正 → 再レビュー（指摘があった場合のループ）**
- 是正は `issue-implementer` へ差し戻す（`pr-reviewer` は push 不可＝コードを書けない）。担当 effort は **②-b でレビューアが決めた降格判断に従う**
  （明確な指摘なら既定 `high`）。
- **再レビューは常に既定 effort（`high`・リスク信号表によらない）**（Issue #120 ⑤・`pr-reviewer` を override なしで dispatch）。
- clean になるまで ②-c を繰り返す。**握りつぶし禁止**：対応不要に見えても FND/Q 起票を主文脈へ提案させ、据え置きはオーナー判断（下記 ③・④）。

**②-d マージ → クローズ → 次へ**
- `pr-reviewer` が genuinely clean と判断したら `gh pr merge`（マージは reviewer 専権）。
- `Closes #N` で自動クローズされなければ主文脈がクローズ（クローズは主文脈がしてよい）。**merge & close を確認してから次 Issue へ**（Issue #120 ②）。

### ③ スコープ拡張は別 Issue に逃がす（PR 肥大化の抑制・Issue #120 ⑧）
レビュー/調査中に**現 PR/Issue のスコープを超える対応**が要ると分かったら、現 PR で直さず **サブ Issue / 別 Issue を起票**（`gh issue create`）。
- `issue-implementer`/`pr-reviewer` は「スコープ外指摘」を報告して STOP する（自分で直さない・AGENTS.md スコープ拡大禁止）。**起票の実行は主文脈**。
- doc-system-v2 に関わる指摘なら FND/Q ノード起票（`verification-author` 経由）も併せて主文脈が判断（AGENTS.md）。

### ④ 先送りは必ずオーナー許可（独断禁止・Issue #120 ⑨ / AGENTS.md スケジュール独断禁止）
指摘・対応を先送り/繰り越すときは、**背景・検討結果・メリデメを提示した上で日本語で許可を取る**。
- **AI が単独で「対応不要」「後でよい」「次スプリント繰り越し」と結論づけない**（AGENTS.md・過去インシデント）。
- `scheduled` は空のまま「今実施 vs 繰り越し＋推奨」を添えて委ねる。判断者と理由をコメント/ノードに明記。

## リスク信号表（②-b 初回レビュー model 選定・bloom-model-tier の軸2を Issue レビューに具体化）
レビュー＝Bloom Lv5 評価。**判断ボトルネック側の信号が1つでも強く立てば `xhigh`、すべて網羅性側なら `high`（既定）**。

| 信号 | `high` 寄り（網羅性ボトルネック） | `xhigh` 寄り（判断ボトルネック） |
|---|---|---|
| ブラストレディアス | 局所（1〜数ファイル・限定モジュール） | コーパス横断・共有資産・多数ノードの ref_version 伝搬 |
| 変更規模 | 小（数十行・定型追加） | 大（構造改変・広域リファクタ） |
| パターンの新規性 | 既存パターン踏襲（テンプレ流し込み・既存に倣う） | 前例なし・新規構造の創出・設計判断を含む |
| 触る対象の性質 | プローズ/資産テキスト・ドキュメント | 権限ゲート/フック/セキュリティ境界・doc-system グラフ構造・型 |
| 可逆性 | 容易に差し戻せる | 不可逆・広範囲に波及 |
| 仕様の明確さ | 受け入れ基準が一意 | 曖昧・利害 trade-off・解釈の余地 |

- 迷ったら **`xhigh` 側に倒す**（bloom-model-tier のタイブレーク＝effort は品質の代理変数にすぎない・安全側）。選定根拠を1行残す（信号→effort）。
- **再レビューは表に依らず常に既定 `high`**（Issue #120 ⑤）。是正の担当 effort は**レビューアの降格判断に従う**（主文脈が決めない・Issue #120 ④）。

## Claude レビュー起動条件表（②-b-2・別モデル視点の投入タイミング）
Claude review MCP は **Codex 初回レビュー後、merge 前**に使う。Codex レビューで明確な修正指摘が出た場合は、まず ②-c で是正し、再レビューで clean に近づいた段階で Claude を呼ぶ（明白な欠陥が残った PR に高コストレビューを重ねない）。

| 条件 | 扱い | 理由 |
|---|---|---|
| 権限ゲート、hook、MCP、rate limit、外部 CLI/API、認証、sandbox、merge/push 境界を変更 | **必須・Opus** | 事故時の影響が大きく、Codex とは別モデルのセキュリティ/運用視点が必要 |
| `AGENTS.md`、custom agent、skill、prompt、レビュー/マージ手順など恒常運用規約を変更 | **必須・Opus** | 以後の全作業へ波及し、自己参照的な見落としが起きやすい |
| doc-system の schema/validator/config、グラフ構造、横断 ref_version、広域 backfill を変更 | **必須・Opus** | 広範囲の不整合やオーナー専権判断の混入を別視点で確認する必要がある |
| リスク信号表で `xhigh`、または reviewer が判断ボトルネックと判定 | **必須・Opus** | Bloom Lv5 評価の判断ボトルネックで、独立視点の価値が高い |
| Codex review と実装者の見解が割れる、または reviewer が「自信不足/未検証」を明示 | **必須・Opus** | merge 前に第三視点で争点を狭める |
| PR が小規模だが、プロンプト/説明文/ユーザー向け運用文言の曖昧さが主リスク | **任意・Fable 追加可** | 表現・解釈・伝わり方の別視点が有効 |
| 局所的なテスト追加、typo、明確な機械的修正、単一ファイルの軽微な doc 更新 | **原則スキップ** | Codex review と通常テストで十分なことが多く、Claude quota を温存する |
| 必須条件に該当するが Claude が rate limit / MCP 障害 | **STOP** | 必須レビューを無断で省かず、待機・例外進行・分割の判断をオーナーに戻す |

記録する1行根拠の形式：
`Claude review: <必須/任意/スキップ/STOP> / model=<opus|fable|opus+fable|none> / trigger=<条件> / timing=<初回後|是正後|再レビュー後> / result=<PRコメントURLまたは未実施理由>`

## 共通指示の配り方（dispatch テンプレをリーンに保つ）
`issue-implementer`/`pr-reviewer` の**恒常的な共通契約**（決定点で前提/背景/メリデメ＋選択肢＋推奨を報告に添える・PR コメントは AI 明記＋具体・
曖昧は STOP 報告・スコープ外は起票提案）は、**各エージェントの `developer_instructions`（`.codex/agents/issue-implementer.toml`／`pr-reviewer.toml`）に常設**する（読者が見る場所・版管理・毎回自動適用）。
- **dispatch prompt には毎回タスク固有情報だけ**を書く。バッチ共通の補足がある場合のみ、AGENTS.md の規約どおり
  `tmp/<sprint>/issue-pipeline-common.md` に書き出して各 dispatch から参照させる（同一指示をコンテキストに展開しない）。
- **Claude review MCP へ渡す恒常指示は `.codex/mcp/claude_review/common_instructions.md` に置く**。MCP が毎回自動注入するため、呼び出し側は「日本語」「AGENTS.md遵守」「読み取り専用」等の共通文言を prompt に繰り返し書かない。
- **恒常契約を毎回 dispatch prompt に展開する仕組みは採らない（設計判断）**：Codex には Claude Code の `SubagentStart` フック（`hookSpecificOutput.additionalContext` で子コンテキストへ注入する仕組み）に相当する機構はない。恒常契約は `developer_instructions` に置くことで可視・版管理でき毎回自動適用されるため、そもそもフック的な注入機構を必要としない。
  理由＝(1) 対象2エージェントは本パイプライン専用で、恒常契約は各 `.toml` に置く方が可視・版管理でき常に効く。
  (2) Codex 版の push/merge 禁止は `.codex/hooks/agent-command-gate.sh` による機械ゲートとプロンプト規律の多層防御だが、hook は静的検査かつ trust 前提なので完全な権限境界ではない。恒常指示の配布は `.toml` と MCP 共通指示に置き、コマンド拒否のような機械判定だけ hook に寄せる（PR2・機械判定と運用ルールを混ぜない）。
  (3) 常時 ON のグローバル副作用は、明示ブロックに比べ保守面が重く不透明で、得られるトークン節約は限定的（この理由は環境非依存でそのまま踏襲）。

## 重い作業は agy を積極利用（Issue #120 ⑦・fail-close）
横断影響調査・参照/孤児調査・スクラッチ計算・並列サブクエリなどの**重い調査**は `agy-delegate` へ回す。
- `agy-delegate` は**移譲前に必ず疎通チェック**し、NG（クラウド/ヘッドレス等）なら**移譲せず主文脈が直接遂行にフォールバック**（fail-close）。
- **正本への書き込み・確定著作・無検証コード採用は移譲しない**（agy 産は素案/レポート＝入力にすぎない・`.codex/agents/agy-delegate.toml` のガバナンス境界）。

## 点検観点（done）
- ① 推奨順を依存グラフ＋根拠付きで提示し、オーナー承認を得た（独断で処理を始めていない）。
- 各 Issue が **implement→PR→review→merge→close** を1件ずつ完結（前 Issue の close 確認後に次へ）。
- 実装 model/effort は bloom-model-tier、初回レビュー effort はリスク信号表で選定し**根拠を1行残した**。是正降格は**レビューアが決めた**。**再レビューは既定 `high`**。
- Claude review MCP の必須/任意/スキップ/STOP を起動条件表で判定し、merge 前に根拠と結果を記録した。
- レビュー指摘・処置結果が **PR レビューコメント**に AI 明記＋具体で残っている（Issue #120 ⑥）。
- スコープ拡張は**別 Issue に逃がした**（現 PR を肥大化させていない・⑧）。
- 先送りは**オーナー許可を取った**（AI 独断で「対応不要/繰り越し」していない・⑨）。
- 主文脈は実装/レビューを自分でやらず、タスク管理・進捗報告・意思決定に専念した（③）。

## 成果物
- 承認済み処置順 ＋ 各 Issue の PR（merge/close 済み）＋ PR レビューコメント（AI 明記）＋ 起票したサブ Issue/FND/Q（あれば）＋ 進捗ログ。
