---
name: impl-design-pipeline
description: Orchestrate the implementation-design phase into a pre-implementation FREEZE SET — architecture-design → orchestration-design → prompt-design, recording design decisions (DD#) and running a spec-inspector total-check. Run only when explicitly invoked (the spec → impl-design bridge). Downstream of spec-pipeline.
---

> **正本 = `.claude/skills/impl-design-pipeline/SKILL.md`**（doc-system v2）。本ファイルはその GitHub Copilot 版ミラー（issue #121 で `.github` 側に新設）。食い違ったら正本に従う。

# 実装設計パイプライン（spec → 実装の橋渡し・凍結セット化）

仕様（spec-pipeline）の下流。論理 DFD＋ドメインモデルが確定してから、実装前に固める設計物を順に・チェックポイント付きで回す。

- **対話が要る段**（総点検の矛盾停止・判断ログ DD# の暫定決定）は主文脈に残す。
- **非対話の並列ノード著作 fan-out は `authoring-fanout`（`author: design-author`）へ委譲**する（下記 2.5）。

## 段
1. 凍結セット索引を立てる（モジュール／IF／プロトコル／永続／オーケストレーション／プロンプト／ログ・版／テスト戦略）。
2. **architecture-design**：モジュール/依存・外部IF・プロトコル・永続。
2.5. **設計層ノード著作 fan-out（非対話）** — 1〜4 が「著作すべき親ノード群」（モジュール一覧・オーケストレーション・プロンプト雛形 等）を確定したら、`authoring-fanout`（`author: design-author`）に委譲する。独立親ノードごとに `targets`（`parent_id`・`kind`・`brief`）で渡し、Wave1（MOD/PORT/PRS/DS）→Wave2（ORC/DM/SCM/CFG/PROMPT）の2波で並列著作させる。単一対象なら fan-out せず `design-author` を直接呼ぶ。`ROLLBACK`/矛盾は主文脈で受け止める。
3. **orchestration-design**：制御フロー・fail-close・ログ/版。（確定後、2.5 と同じ経路で ORC ノードを著作）
4. **prompt-design**：LLM 雛形・役割制約・注入対策。（確定後、2.5 と同じ経路で PROMPT ノードを著作）
5. **テスト戦略**：test-strategy（テーラリング済）を適用。
6. **総点検**：spec-inspector に設計ドキュメント群を点検させ、G# を反映。
7. **判断ログ**：仕様で一意に決まらない点を DD#（原案→比較→推奨→暫定決定→影響範囲）で記録。

## 成果物
設計索引（凍結セット）＋ architecture/orchestration/prompt 各設計 ＋ 判断ログ（DD#）＋ doc-system-v2 設計層ノード（`authoring-fanout` 経由で著作・反映済み）。
