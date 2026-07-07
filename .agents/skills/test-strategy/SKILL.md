---
name: test-strategy
description: Test strategy for THIS project (review-system) — unittest per public function, TD (Markdown test design) + TC (Python unittest code) + TR (test result with result/log_ref frontmatter), commit-before-test, same 3-set for Codex CLI e2e. Use when planning HOW to test the implementation. NOT spec/design (see domain-model/schema-design), NOT asset auditing (see asset-auditor).
status: tailored (active) — derived from .claude/standards/test-strategy
---

# テスト戦略（review-system テーラリング済・active）

> 汎用標準 [`.claude/standards/test-strategy`](../../../.claude/standards/test-strategy/SKILL.md) の**不変条件を継承**し、本PJのノブを埋めた版。
> 由来・差分は [tailoring-registry](../../../.claude/tailoring-registry.md)。実装の足場は [design/02 モジュール構成](../../../docs/design/02-module-architecture.md)。
> doc-system の **TD/TC/TR 3層**（[DD-009](../../../docs/doc-system/02-meta-schema.md)）に対応済み（移行ログ: [backups/2026-06-10](../../../.claude/backups/2026-06-10/MIGRATION-LOG.md)）。

## doc-system との対応

| doc-system 型 | 本PJの実体 | 置き場 | ID prefix |
|---|---|---|---|
| **TD**（テスト設計） | テスト設計 Markdown（目的/前提/手順/期待結果） | `tests/designs/<id>.md` | `TD-<area>-<nnn>` |
| **TC**（テストコード） | Python unittest コード | `tests/unit/` | TC- prefix は不要（ファイル名で管理） |
| **TR**（テスト結果） | テスト結果 Markdown（ケースコピー＋実測） | `tests/reports/<id>-<commit>.md` | `TR-<area>-<nnn>-<commit>` |
| ログ | stdout ダンプ（TR の log_ref が参照） | `tests/logs/<id>-<commit>.txt` | — |

## TD ノード著作 fan-out（非対話・エージェント委譲・issue #121）

上記「本PJの実体」（`tests/designs/*.md` 等）とは別に、doc-system-v2 の在グラフ表現として **TD ノード**（`04-verification/td`・→ SPEC・`condition` が対応 SPEC と一致）を著作する。凍結セット（SPEC 群）が確定し、対応する TD の親（SPEC 単位）が複数・独立にバッチ着手できる状態になったら、著作を主文脈で場当たりに行わず **`authoring-fanout`** エージェントに **`author: verification-author`** で委譲する：

- 独立 SPEC ごとに `targets` 配列（`parent_id`＝対象 SPEC の slug・`kind: TD`・`brief`）で渡し、**並列著作**させる。
- TC/TR は実装・実行が先行条件のため本 fan-out の対象外（TD 確定後、実装着手→コミット→テスト実行を経て別途 verification-author で個別に著作する）。
- 単一 SPEC しか無い段では fan-out せず `verification-author` を直接呼ぶ（fan-out はオーバースペック）。
- 戻りが `FANOUT_DONE` なら次段（実装・テスト実行）へ。**`ROLLBACK`/`STOP`/矛盾報告が返ったら主文脈で受け止め**、`verification-author` の再起動 or PR7 起票（Q/DD → オーナー）を行う（subagent はユーザーへ直接質問せず、主文脈が日本語で質問する）。
- 対話が要る段（TD の condition と SPEC の不一致など矛盾の裁定）は主文脈に残す（DD-22 ①-C ハイブリッド）。

## 継承する不変条件（標準のまま）
unittest 基本／テスト設計＝Markdown（TD）／テスト結果＝TD コピー＋実測＋commit id（TR）／ログ＝標準出力ダンプをリンク／
失敗も残す（隠蔽・上書き禁止＋原因/対策）／e2e も同じ3点セット／**テスト前にコミット**。3点セットの対応を保つ。

## 本PJのノブ（埋めた値）

| ノブ | 本PJの決定 |
|---|---|
| 「1関数」の定義・網羅 | `domain` / `core` / `parsing` / `prompts` の**全 public 関数**を unittest（[02](../../../docs/design/02-module-architecture.md) の内向き依存で純粋なので関数単位で回せる） |
| 非決定の決定化シーム | **`adapters/fake.py` の `FakePlatformAdapter`（record/replay フィクスチャ）**。非決定は LLM のみ＝`PlatformPort` の裏。**アダプタ境界＝テスト境界**にして core を決定化（[10 境界](../../../docs/requirements/10-llm-system-boundary.md)・E） |
| e2e の駆動・対象 | **Codex CLI エージェントが `io/cli` を stdout 駆動で実行**。対象＝代表レビューシナリオ（合成→評価→仕分け→適用→レポート）。3点セットを残す |
| ログ取得 | **標準出力ダンプ**。`python -m unittest -v` 出力＋アプリ stdout を `tee` で `tests/logs/<id>-<commit>.txt` に保存 |
| ディレクトリ配置 | `tests/unit/`（TC: Python）・`tests/designs/*.md`（TD: テスト設計）・`tests/reports/*.md`（TR: テスト結果）・`tests/logs/*.txt`（ログ） |
| バージョニング | TD frontmatter に `version`。TR frontmatter に **`result: PASS\|FAIL`・`log_ref`** ＋ ヘッダに `{ TD版 + 実装commit id + プロンプト雛形版 + 基準content_hash(S6) + 実行日時 }`（[S6 版スタンプ](../../../docs/requirements/13-stabilization.md) と一致） |
| 実行ランナー | **`python -m unittest`**（標準ライブラリのみ・[Q5](../../../docs/dashboard.md)） |

## 3点セットのテンプレ（本PJ）

**TD（テスト設計）** `tests/designs/<id>.md`
```
---
id: TD-<area>-<nnn>
version: 1
condition: normal   # normal | boundary | empty | failure | error（doc-system SPEC.condition に合わせる）
---
# 目的 / 前提 / 手順 / 期待結果
```

**TR（テスト結果）** `tests/reports/<id>-<commit>.md` … TD を丸ごとコピーし末尾に追記
```
---
（TD のフロントマターをコピー）
result: PASS        # PASS | FAIL（RULE-020 対応）
log_ref: tests/logs/<id>-<commit>.txt   # FAIL 時は必須（RULE-021 対応）
---
（TD の本文そのまま）

## 実測
- ヘッダ: { TD版 / 実装commit id / プロンプト雛形版 / 基準content_hash / 実行日時 / 環境 }
- ログ: tests/logs/<id>-<commit>.txt
- （FAIL時）根本原因 / 対処   ← 隠蔽・上書き禁止（PR8）
```

**ログ** `tests/logs/<id>-<commit>.txt` … stdout ダンプ（TR の `log_ref` から参照）。

## 手順（1サイクル）
1. 実装を**コミット**（commit id を確定）。
2. `python -m unittest -v 2>&1 | tee tests/logs/<id>-<commit>.txt`。
3. TD をコピーして TR を作成、frontmatter に `result` と `log_ref` を追記。
4. FAIL は TR を残し、根本原因・対処を併記（消さない・上書きしない）。
5. e2e は Codex CLI エージェントで `io/cli` を回し、同じ3点セット（TD/TC/TR/ログ）を残す。
