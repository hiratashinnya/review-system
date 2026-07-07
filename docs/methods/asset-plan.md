# 資産化プラン — メソッドをスキル/エージェントにする計画・提案

> [method-inventory.md](method-inventory.md) で棚卸した A1–A14 ＋原則 PR1–10 を、**Claude Code のスキル/サブエージェント**として再利用可能にした記録（実装済み）。
> これらは review-system 専用ではなく、**今後どんな仕様策定でも使える横断資産**（汎用・プロジェクト非依存）。

## 1. スキルか？エージェントか？（振り分けの判断基準）

| 形式 | 使う場面 | 特徴 |
|---|---|---|
| **スキル**（`/name`・SKILL.md） | メインスレッドが**その場で従う手順・チェックリスト**。ユーザーとの対話・判断が要る、比較的短い手続き | 手順書を注入して実行。状態は会話に残る |
| **サブエージェント**（agent 定義） | **大きい・ファンアウト・ほぼ自走**して結論だけ返す仕事。読み込み量が多くコンテキストを隔離したい | 別コンテキストで走り、結論を返す。点検/分解の重い処理向き |
| **共有リファレンス**（`spec-principles` skill, `user-invocable:false`） | 全スキル/エージェントが参照する**決めた基準**（PR1–10） | 単独実行しない。スキルは相対リンク参照・エージェントは `skills:` でプリロード |

判断則：**対話と判断が中心 → スキル**／**読み込み・分解・点検が中心で自走 → エージェント**。

## 2. 振り分け案（A# → 資産）

| A# 活動 | 資産 | 形式 | 名前（案） | 優先 |
|---|---|---|---|---|
| 原則 PR1–10 | 共有リファレンス | `spec-principles` skill（`user-invocable:false`） | — | **1** |
| A6 カバレッジ点検 ＋ A10 入出力点検 ＋ A11 漏れ/矛盾ハント | 点検ループ | **エージェント** | `spec-inspector` | **1** |
| A7 構造化分析 ＋ A8 状態インベントリ | DFD 分解 | **エージェント** | `structured-analysis` | **2** |
| A9 価値経路トレース | レベリング点検 | スキル | `/value-trace` | 2 |
| A12 価値ベース MVP スコープ | 価値分析 | スキル | `/mvp-scope` | 2 |
| A4 I/O 台帳 ＋ A5 イベントリスト | 台帳起こし | スキル | `/io-event-ledger` | 3 |
| A1 認識合わせ | 段取り | スキル | `/align` | 3 |
| A13 スキーマ設計 | スキーマ起こし | スキル | `/schema-design` | 3 |
| A15 ドメインモデル設計（DD→型安全クラス） | 内部型起こし | スキル | `/domain-model` | 3 |
| A2 ダッシュボード運用 / A3 案出し | 作業流儀 | （CLAUDE.md の作業規約に記述） | — | 3 |
| A1→A12 全体 | パイプライン | スキル（オーケストレータ） | `/spec-pipeline` | 4 |
| A14 資産化（重複/競合監査） | 資産監査 | **エージェント** | `asset-auditor` | 5 |
| A14 資産化（パイプライン） | オーケストレータ | スキル | `/asset-pipeline` | 5 |
| ④ テスト戦略（汎用標準） | 標準（非活性） | standards | `test-strategy-standard`（`.claude/standards/`） | 6 |
| ④ テスト戦略（本PJ） | テーラリング済 active | スキル | `/test-strategy`（`.claude/skills/`） | 6 |
| A16 テーラリング運用 | 機構＋台帳 | standards/＋registry | `.claude/tailoring-registry.md` | 6 |
| A17 アーキテクチャ設計（モジュール/IF/プロトコル/永続） | 実装設計 | スキル | `/architecture-design` | 7 |
| A18 オーケストレーション設計（制御フロー/fail-close/ログ） | 実装設計 | スキル | `/orchestration-design` | 7 |
| A19 プロンプト設計（LLM 雛形/役割/注入対策） | 実装設計 | スキル | `/prompt-design` | 7 |
| A20 実装設計パイプライン（凍結セット） | オーケストレータ | スキル（disable-model-invocation） | `/impl-design-pipeline` | 7 |
| 8 判断ログ DD# ／ 9 凍結セット規律 | 作業流儀 | （CLAUDE.md の作業規約に記述・スキル化しない） | — | 7 |
| 設計総点検 | 既存拡張 | エージェント | `spec-inspector`（点検対象に設計ドキュメント追加） | 7 |
| Issue #3 資産の横展 | 横展オーケストレータ | スキル＋Python ヘルパー | `/asset-lateral-deploy` | 8 |
| 外部 CLI 委譲（agy/Antigravity） | 外部委譲ツール | スキル（薄い起動口・disable-model-invocation）＋エージェント | `/agy-delegate`・`agy-delegate` | — |
| Issue 運用（implement→PR→review→merge→close） | Issue 処理オーケストレータ＋ファンアウト2種＋権限フック | スキル（disable-model-invocation）＋エージェント2＋PreToolUse フック | `/issue-pipeline`・`issue-implementer`・`pr-reviewer`（＋`.claude/hooks/agent-command-gate.sh`） | — |
| ノード検索/読み込み（md2idx 思想） | 検索・コンテキスト効率 | スキル（CLI 利用手順）＋エージェント（検索ループ隔離） | `/docidx`・`docidx-lookup`（実体＝`docidx/`） | — |

> `docidx` を**スキル＋エージェント両方**にする理由：スキルは `python -m docidx` の利用手順（メインスレッドがその場で叩く）。エージェント `docidx-lookup` は「検索→選別→show→要約」の反復を別コンテキストに隔離し、ダイジェストだけ返してメインの文脈を節約する自走仕事。責務は**取得（retrieval）**で、点検（`spec-inspector`）・価値経路（`/value-trace`）・著作（`*-author`）とは別軸（asset-auditor 監査済・新規）。

> `spec-inspector` と `structured-analysis` を**エージェント**にする理由：複数ファイルを横断的に読み・分解し、結論（gap 一覧 / DFD 一式）を返す自走型で、メインの会話文脈を汚さない方が効く（[method-inventory](method-inventory.md) の依存図でも A10/A11 が反復ループの核）。

## 3. ディレクトリ構成（案）

```
.claude/
  skills/
    spec-principles/SKILL.md   # PR1–10（user-invocable:false／agent が skills: でプリロード）
    align/SKILL.md             # A1
    io-event-ledger/SKILL.md   # A4+A5
    value-trace/SKILL.md       # A9
    mvp-scope/SKILL.md         # A12
    schema-design/SKILL.md     # A13
    domain-model/SKILL.md      # A15（DD 確定後の内部型/クラス設計・実装フェーズ）
    spec-pipeline/SKILL.md     # A1→A12 仕様設計オーケストレータ
    asset-pipeline/SKILL.md    # A14 資産化オーケストレータ（disable-model-invocation）
    test-strategy/SKILL.md     # ④ テスト戦略（本PJ テーラリング済・active）
    architecture-design/SKILL.md   # A17 モジュール/依存・IF・プロトコル・永続
    orchestration-design/SKILL.md  # A18 制御フロー・fail-close・ログ/版
    prompt-design/SKILL.md         # A19 LLM 雛形・役割制約・注入対策
    impl-design-pipeline/SKILL.md  # A20 実装設計オーケストレータ（disable-model-invocation）
    issue-pipeline/SKILL.md        # Issue #120 Issue 処理オーケストレータ（disable-model-invocation・dev-tooling メタパイプライン）
  standards/                   # A16 汎用標準（非活性・auto-load されない）
    test-strategy/SKILL.md     # ④ テスト戦略の汎用標準（不変条件＋ノブ一覧）
  agents/                      # ※ 現況の正本は tailoring-registry.md（本ツリーは設計初期スナップショット）
    spec-inspector.md          # A6+A10+A11（仕様点検→gap 一覧を返す）
    structured-analysis.md     # A7+A8（コンテキスト→DFD→単一責務→状態）
    asset-auditor.md           # A14 既存資産の重複/矛盾/競合監査（read-only／standards も棚卸し対象）
    docidx-lookup.md           # ノード検索/読み込み（docidx CLI・retrieval・read-only）
    requirements-author.md     # VAL/SR/FR/NFR 著作（Policy B・型別著作エージェント）
    spec-author.md             # SPEC 著作（1アサーション1ノード）
    analysis-author.md         # ACTOR/I/O/P/E 著作
    design-author.md           # ORC/DS/MOD/DM/PORT/PRS/SCM/CFG/PROMPT/TERM 著作
    verification-author.md     # TD/TC/TR/VERIFY/FND/DD/Q/PEND 著作
    reconciliation-validator.md  # 著作後の read-only 構造検証→VALIDATION_OK/ROLLBACK（Write/Edit なし＝fail-close・DD-22）
    reconciliation.md          # 検証合格後の self_fix 適用＋本ファイル確定書込＋tmp 掃除（書込専任・DD-22）
    agy-delegate.md            # 外部 CLI(agy) 委譲
    issue-implementer.md       # Issue #120 1 Issue を実装→PR（merge 不可・agent-command-gate 機械強制）
    pr-reviewer.md             # Issue #120 PR レビュー→merge（push 不可・agent-command-gate 機械強制）
  hooks/
    agent-command-gate.sh      # Issue #120 PreToolUse・issue-implementer/pr-reviewer の push/merge 非対称権限を機械強制
  tailoring-registry.md        # A16 標準⇄テーラリングの対応・実体パス・差分（agents の正本）
CLAUDE.md                      # A2/A3 の作業流儀＋「迷ったら spec-principles」
```

- **project 直下（`.claude/`）に置き repo にコミット済み**。安定したら user 級（`~/.claude/`）へ昇格して全プロジェクトで共有。
- **可搬性のため、資産から `docs/methods/*` へは逆リンクしない**（method-inventory は人間向け根拠として残す）。原則は `spec-principles` を単一ソースにする（DRY）。

## 4. 各資産の中身テンプレ

**SKILL.md**（例：`/io-inspect` 相当を io-event-ledger に内包）
```
---
name: <名前>
description: いつ使うか（トリガを具体的に）
---
## 参照
- 原則：[spec-principles](../spec-principles/SKILL.md)（PR1, PR6 …）
## 手順
1. … 2. …（method-inventory の A# の手順をそのまま）
## 判断基準
- …（A# の判断基準）
## 点検観点（done の条件）
- …（A# の点検観点）
## 成果物テンプレ
- 表/図のひな形
```

**agent 定義**（例：`spec-inspector`）
```
---
name: spec-inspector
description: 台帳/イベント/設計を横断点検し gap 一覧(G#)を返す。矛盾は停止して報告。
tools: Read, Grep, Glob   # 読み取り中心。書き込みはしない
---
（system prompt に PR1–10 と A6/A10/A11 の手順・点検観点を埋め込む。
 出力＝gap 表 ＋ 矛盾があれば「停止・要確認」マーカー）
```

## 5. 着手順の提案（資産化フェーズ）

1. **`spec-principles` skill**（PR1–10）＋ **`spec-inspector` エージェント** … いま最も繰り返し使う点検ループを先に固める。
2. **`structured-analysis` エージェント** … 最も重く独自性の高い手法を再現可能に。
3. **`/value-trace`・`/mvp-scope`** スキル … 設計後半の価値点検を軽量化。
4. **`/io-event-ledger`・`/align`・`/schema-design`** スキル … 前半の起こし作業。
5. **`/spec-pipeline`**（オーケストレータ）＋ **CLAUDE.md の作業規約** … 全体を1コマンドで回せるように。

## 6. 確定事項（実装済み）

- 置き場所：**project 直下 `.claude/`**（コミット済み）。安定後に user 級へ昇格可。
- スコープ：**汎用（プロジェクト非依存）**。固有版は提案時に併記し、採用は汎用版。
- 全資産を実体化済み：`spec-principles` / `spec-inspector` / `structured-analysis` / `/value-trace` / `/mvp-scope` / `/io-event-ledger` / `/align` / `/schema-design` / `/spec-pipeline` ＋ `CLAUDE.md`。
- **資産化そのものも資産化（A14）**：`asset-auditor`（重複/矛盾/競合監査・read-only）＋ `/asset-pipeline`（オーケストレータ）。
  新資産は**作る前に `asset-auditor` で点検**し、新規 vs 既存変更を判断する。
- **テーラリング運用（A16）**：汎用標準は `.claude/standards/`（非活性・auto-load されない）、テーラリング済 active は `.claude/skills/`、対応は `.claude/tailoring-registry.md`。
  §6 の「固有版は提案時に併記し採用は汎用版」を、**標準（汎用）⇄テーラリング（固有）の常設機構**へ格上げ。初回適用＝`test-strategy`（④）。
- **実装設計フェーズの資産化（A17–A20）**：設計工程を 3 焦点スキル（`/architecture-design`＝1+2+3+4・`/orchestration-design`＝5+7・`/prompt-design`＝6）＋オーケストレータ `/impl-design-pipeline` に集約（9個に割らない＝PR1）。
  8（判断ログ DD#）・9（凍結セット規律）は**作業規約**（CLAUDE.md）に。総点検は **spec-inspector の拡張**（設計ドキュメントを点検対象に追加）で賄い、新規エージェントは作らない。
  これら設計スキルは**汎用メソッド（プロジェクト非依存）**として `.claude/skills/` に active（本PJ固有の選択＝ヘキサゴナル/内部git/stdout プロトコルは成果物 docs 側）。テーラリングが要る場合のみ registry へ起票。
