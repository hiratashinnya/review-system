---
name: test-strategy
description: Test strategy for THIS project (review-system) — unittest per public function, TD (Markdown test design) + TC (Python unittest code) + TR (test result with result/log_ref frontmatter), commit-before-test, same 3-set for end-to-end. Use when planning HOW to test the implementation. NOT spec/design, NOT asset auditing.
---

# テスト戦略（review-system テーラリング済）

## 実行ランナー

`python -m unittest discover -s tests -p "test_*.py"`（標準ライブラリのみ）

## 3点セット（TD / TC / TR）

| 種別 | 置き場 | 形式 |
|---|---|---|
| **TD**（テスト設計） | `tests/designs/<id>.md` | Markdown（目的/前提/手順/期待結果） |
| **TC**（テストコード） | `tests/unit/` | Python unittest |
| **TR**（テスト結果） | `tests/reports/<id>-<commit>.md` | TD コピー＋実測（result/log_ref frontmatter 必須） |
| **ログ** | `tests/logs/<id>-<commit>.txt` | stdout ダンプ（`python -m unittest -v 2>&1 \| tee`） |

## 手順（1サイクル）

1. 実装を**コミット**（commit id を確定）。
2. `python -m unittest -v 2>&1 | tee tests/logs/<id>-<commit>.txt`。
3. TD をコピーして TR を作成、frontmatter に `result: PASS|FAIL` と `log_ref` を追記。
4. FAIL は TR を残し、根本原因・対処を併記（消さない・上書きしない）。

## 本PJ のノブ

- **テスト対象**：`domain` / `core` / `parsing` / `prompts` の全 public 関数。
- **非決定の決定化**：`adapters/fake.py` の `FakePlatformAdapter`（record/replay フィクスチャ）。アダプタ境界＝テスト境界。
- **バージョニング**：TR frontmatter に `result: PASS|FAIL`・`log_ref`（PASS でも必須）。

## TD テンプレ

```
---
id: TD-<area>-<nnn>
version: 1
condition: normal   # normal | boundary | empty | failure | error
---
# 目的 / 前提 / 手順 / 期待結果
```
