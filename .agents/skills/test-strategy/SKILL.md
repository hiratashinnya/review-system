---
name: test-strategy
description: 本プロジェクト review-system のテスト戦略。公開関数ごとの unittest、TD/TC/TR の 3 点セット、commit-before-test、Codex CLI e2e の同形式を扱う。実装のテスト方法を計画する時に使い、仕様/設計や資産監査には使わない。
---

すべての説明・報告・質問は日本語で行う。ユーザーが明示的に別言語を指定した場合を除き、この skill の応答も日本語に統一する。

# テスト戦略（review-system テーラリング済・active）

> 汎用標準を Codex 用に移した本 skill の**不変条件を継承**し、本 PJ のノブを埋めた版。移植元の旧テスト標準は比較用としてのみ参照する。
> 由来・差分は旧 tailoring registry を比較用に確認する。実装の足場は [design/02 モジュール構成](../../../docs/design/02-module-architecture.md)。
> doc-system の **TD/TC/TR 3層**（[DD-009](../../../docs/doc-system/02-meta-schema.md)）に対応済み。

## doc-system との対応

| doc-system 型 | 本PJの実体 | 置き場 | slug 方針 |
|---|---|---|---|
| **TD**（テスト設計） | 1テストシナリオのサイドカー。本文はテストプログラム単位の共有 Markdown を `body_ref.file`/`body_ref.anchor` で参照 | `doc-system-v2/nodes/04-verification/td/{slug}.yaml` + 共有本文 | `slugify(title)` |
| **TC**（テストコード） | Python unittest の実テスト識別子。Markdown 本文なし、`test.file`/`test.qualname`/`test.kind` が正本 | `doc-system-v2/nodes/04-verification/tc/{slug}.yaml` | `slugify(title)` |
| **TR**（テスト結果） | テスト結果ノード。`result`/`log_ref` はサイドカー、本文は実測要約 | `doc-system-v2/nodes/04-verification/tr/{slug}.{yaml,md}` | `slugify(title)` |
| ログ | stdout ダンプ（TR の log_ref が参照） | `tests/logs/<id>-<commit>.txt` | — |

## TD ノード著作 fan-out（非対話・エージェント委譲・issue #121）

doc-system-v2 の在グラフ表現として **TD ノード**（`04-verification/td`・→ SPEC・`condition` が対応 SPEC と一致・`body_policy=shared`）を著作する。凍結セット（SPEC 群）が確定し、対応する TD の親（SPEC 単位）が複数・独立にバッチ着手できる状態になったら、著作を主文脈で場当たりに行わず **`authoring-fanout`** エージェントに **`author: verification-author`** で委譲する：

- 独立 SPEC ごとに `targets` 配列（`parent_id`＝対象 SPEC の slug・`kind: TD`・`brief`）で渡し、**並列著作**させる。
- TC/TR は実装・実行が先行条件のため本 fan-out の対象外（TD 確定後、実装着手→コミット→テスト実行を経て別途 verification-author で個別に著作する）。TC は `body_policy=none` のため Markdown 本文を作らず、`test.*` で実テスト識別子を指す。
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
| ディレクトリ配置 | `tests/unit/`（実テストコード）・`doc-system-v2/nodes/04-verification/td/`（TD サイドカー + shared body）・`doc-system-v2/nodes/04-verification/tc/`（TC bodyless サイドカー）・`doc-system-v2/nodes/04-verification/tr/`（TR）・`tests/logs/*.txt`（ログ） |
| バージョニング | TD/TC/TR の `version` は各サイドカー。TR サイドカーに **`result: PASS\|FAIL`・`log_ref`** ＋ 本文に `{ TD版 + 実装commit id + プロンプト雛形版 + 基準content_hash(S6) + 実行日時 }`（[S6 版スタンプ](../../../docs/requirements/13-stabilization.md) と一致） |
| 実行ランナー | **`python -m unittest`**（標準ライブラリのみ・[Q5](../../../docs/dashboard.md)） |

## 3点セットのテンプレ（本PJ）

**TD（テスト設計）** `doc-system-v2/nodes/04-verification/td/{slug}.yaml`
```yaml
title: "テストシナリオ名"
version: "0.1.0"
condition: normal   # SPEC.condition に合わせる
labels: []
scheduled: "sprint-N"
body_ref.file: "nodes/04-verification/td/test_program_shared_body.md"
body_ref.anchor: "scenario-a"
edges:
  - to: "検証する-spec-slug"
    ref_version: "0.1"
```

**TD shared body** `doc-system-v2/nodes/04-verification/td/test_program_shared_body.md`
```markdown
## scenario-a

**目的**: [...]
**前提**: [...]
**手順**: [...]
**期待結果**: [...]
```

**TC（テストコード）** `doc-system-v2/nodes/04-verification/tc/{slug}.yaml`
```yaml
title: "テスト実装名"
version: "0.1.0"
labels: []
scheduled: "sprint-N"
test.file: "tests/unit/test_example.py"
test.qualname: "TestExample.test_case"
test.kind: "unittest"
edges:
  - to: "対応する-td-slug"
    ref_version: "0.1"
```

**TR（テスト結果）** `doc-system-v2/nodes/04-verification/tr/{slug}.yaml` + `{slug}.md`
```
title: "テスト実行名 PASS"
version: "0.1.0"
labels: []
scheduled: "sprint-N"
result: PASS
log_ref: tests/logs/<slug>-<commit>.txt
edges:
  - to: "生成元-tc-slug"
    ref_version: "0.1"
```

TR 本文:
```markdown
## 実測
- ヘッダ: { TD版 / 実装commit id / プロンプト雛形版 / 基準content_hash / 実行日時 / 環境 }
- ログ: tests/logs/<slug>-<commit>.txt
- （FAIL時）根本原因 / 対処   ← 隠蔽・上書き禁止（PR8）
```

**ログ** `tests/logs/<id>-<commit>.txt` … stdout ダンプ（TR の `log_ref` から参照）。

## 手順（1サイクル）
1. 実装を**コミット**（commit id を確定）。
2. `python -m unittest -v 2>&1 | tee tests/logs/<id>-<commit>.txt`。
3. TC bodyless サイドカーを `test.*` 付きで作成し、TD-TC を 1:1 に保つ。
4. TR サイドカーに `result` と `log_ref`、TR 本文に実測を記録する。
5. FAIL は TR を残し、根本原因・対処を併記（消さない・上書きしない）。
6. e2e は Codex CLI エージェントで `io/cli` を回し、同じ3点セット（TD/TC/TR/ログ）を残す。
