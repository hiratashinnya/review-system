# Repository Instructions for GitHub Copilot

This repository uses a structured spec-design methodology. Below are the core principles and available skills.

## Core Principles (spec-principles)

# 仕様設計・点検の原則（PR1–PR10）

仕様策定・構造化分析・点検で迷ったら立ち返る横断原則。各スキル/エージェントが参照する単一ソース。

- **PR1 もので分ける（発生源基準）** — 入出力は「**もの（実体）＋発生源（外部アクター）**」だけで分ける。**使い道**や**内部の発生プロセス**では分けない。発生源が外部システム/LLM のものは**入力**（システムはそれをラップして価値を出す）。外から見れば内部プロセスが違っても等しく「システム出力」。同じものを発生プロセス違いで割らず、違うものは分ける。
- **PR2 2軸（判定の種類を混ぜない）** — **機械判定**（順序のある属性＝自動でゲートできる）と**運用ルール**（事実性・妥当性＝人が確認）を分ける。運用ルールは設計で詰めず、**機構＋デフォルト**に留める。
- **PR3 系外＝非イベント** — システムを介さない変更（ファイル直接編集など）は**イベント化・入力化しない**。必要な検査は**処理時に毎回**実行して警告する。
- **PR4 観測できないものは持たない** — 顛末をシステムが観測できない事象に対する機能は作らない。
- **PR5 状態の要否** — 毎回作り直せる → **無状態**。過去を覚えていないと成立しない（取り消し・既出判定・蓄積）→ **状態**。導出物は状態化しない。
- **PR6 価値経路を遮断しない** — すべての入力が、プロセスを通って**価値（出力）まで連続**して届くこと。途切れ＝設計の穴。
- **PR7 矛盾は停止して打ち上げ（空で止めない）** — 既存決定と両立しない事実は勝手に解決せず**止めて確認**する。ただし**止めるときも原案・比較・理由付き推奨を必ず添える**（意見なき停止は禁止）。**止める前に必ずノードを起票する**：未決論点・質問＝**Q ノード**（`type: Q`・決定で DD へ昇格）／既存ノードへの指摘・矛盾＝**FND ノード**。質問はダッシュボードでなく Q ノードに起票する。**①ノード起票 → ②ダッシュボード更新（Q/FND いずれも必須）→ ③推奨を添えて停止** の順を守り、チャットで述べるだけの未起票停止は禁止。FND を resolved にしたら処置対象に `→FND-x` 辺を付与。**FND 起票時は `edges[].ref_version` の値を本文にも明記する**（辺逆転後も指摘時の版を追跡できる・DD-3 規約）。フェーズで対応を変える：**要件は暫定で進めず止めて他を進める／設計は推奨案で暫定決定し DD# に記録**。
- **PR8 フル論理設計＋MVP印** — 論理は完全に作り、MVP で削る所は**印で残す**（消さない）。
- **PR9 DFD レベリング** — 階層をまたぐ時に**上位/下位へ直接繋がない**。外部・データストアは L1 境界に繋ぎ、リーフへは親を経由（`外部→L1→leaf`）。プロセスから出る時も同様。
- **PR10 認識合わせ先行** — 着手前に手順を整理・提案し、不明点を質問してから動く。重い作業ほど先に握る。

## Available Skills

| Skill | Description |
|-------|-------------|
| `/align` | Pre-work alignment. Decompose the request, propose the steps and granularity, ask the open questions, and declare the fixed parameters before starting. Use before any multi-step design task. |
| `/architecture-design` | Design the PHYSICAL module/dependency architecture from a SETTLED logical DFD + domain model — hexagonal ports & adapters, dependency-inward, a single composition root, the CLI/interface surface with exit codes, platform/protocol ports + a driven protocol, and persistence repository ports with transactions. Use AFTER structured-analysis (logical decomposition) and domain-model. NOT logical DFD decomposition (use structured-analysis), NOT external file-format schema (use schema-design). |
| `/asset-lateral-deploy` | 資産の横展方法確立。.claude 配下の資産を棚卸しし、ターゲットプラットフォーム（GitHub Copilot 等）向けにフォーマット変換してPRを作成する。スラッシュコマンド一発で一気通貫実行。 |
| `/asset-pipeline` | Orchestrate the asset-ization pipeline (method -> skill/agent) in the main thread — inventory, asset-auditor reuse/conflict check, proposal (generic vs project-specific), phased build with checkpoints, verification gate. Run only when explicitly invoked. |
| `/bloom-model-tier` | Assign a Claude model tier to a sub-agent's frontmatter `model:` field by classifying its dominant Bloom's-revised cognitive level (Remember→haiku, Understand/Apply→sonnet, Analyze/Evaluate/Create→opus). Use when deciding which model a custom agent should run on. NOT runtime control-flow or version-stamp logging (orchestration-design), NOT prompt template design (prompt-design). |
| `/coverage-html` | Generate a coverage HTML report for this project using unittest discover. Installs coverage if absent, runs all tests under tests/, writes htmlcov/index.html, and prints a per-module summary. Use when you want to see which lines are covered or uncovered. |
| `/domain-model` | Derive a type-safe, immutable in-code domain model from a SETTLED data dictionary / I/O ledger — wrap meaningful scalars as value objects (no primitive/tuple obsession), make closed vocabularies enums, prefer frozen dataclasses, choose constructor vs factory vs builder deliberately, and name everything self-explanatorily. Use AFTER the data dictionary is settled, when turning it into Python types/classes. Not for external file-format schemas (use schema-design) and not for producing the data dictionary itself (use structured-analysis). |
| `/impl-design-pipeline` | Orchestrate the implementation-design phase into a pre-implementation FREEZE SET — architecture-design → orchestration-design → prompt-design, recording design decisions (DD#) and running a spec-inspector total-check. Run only when explicitly invoked (the spec → impl-design bridge). Downstream of spec-pipeline. |
| `/mvp-scope` | Scope an MVP by value. List features with value/precondition/atomic-group, draw a dependency DAG, then propose build order and where to draw the MVP line. Use after features are enumerated and before development starts. |
| `/orchestration-design` | Design the RUNTIME control flow — a swimlane flowchart (lanes = actors/layers), staged outcomes (a Result type) with fail-close paths, execution-order invariants, plus log-channel separation and version stamping. Use when turning a settled module architecture into an end-to-end execution design. This is control-flow design, NOT value-path inspection (use value-trace) and NOT logical DFD decomposition (use structured-analysis). |
| `/prompt-design` | Design LLM system-prompt templates — role constraints, prompt assembly (a builder), prompt-injection defenses, and a template catalog with MAJOR.MINOR versions. For output schemas use schema-design; for version stamps see test-strategy / logging design. Use when designing HOW an LLM is prompted inside a wrapping system. NOT external config-file schema (schema-design), NOT runtime control flow (orchestration-design). |
| `/schema-design` | Design a structured config/criteria file schema reader-first — list readers, use a frontmatter (machine) + body (human/LLM) two-layer split, route attributes by the two axes, and disambiguate with samples. Use when an external settings/criteria file format is needed. |
| `/spec-pipeline` | Orchestrate the full spec-design pipeline in the main thread — align, I/O & event ledger, inspect, structured analysis, value trace, MVP scope. Run only when explicitly invoked. |
| `/test-strategy` | Test strategy for THIS project (review-system) — unittest per public function, TD (Markdown test design) + TC (Python unittest code) + TR (test result with result/log_ref frontmatter), commit-before-test, same 3-set for Claude Code e2e. Use when planning HOW to test the implementation. NOT spec/design (see domain-model/schema-design), NOT asset auditing (see asset-auditor). |
| `/value-trace` | Trace each event from input through processes to output as source\|info\|receiver triples, verifying DFD leveling (no level-skipping) and flagging any severed value path. Use to total-check a process design against the event list. |
