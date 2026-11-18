# Issue #578「harness と dsv2 の既存テストコードを tests/道具名/ へ移設する」

- URL: https://github.com/hiratashinnya/review-system/issues/578
- 状態: open（2026-11-18取得）
- 本文: 4415文字/ 89行。全文: `../raw/issues-2026-10.jsonl`
- AC: 8件（未チェック: 8）
- Issue参照: #571, #577, #542, #538, #540
- PR参照: #571
- 主見出し: ## 目的・背景 | ## 現状と根拠（2026-10-06 時点、`ls tests/unit` による） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 代替案（オーナー判断で不採用・2026-10-06） | ## Project fields（実行環境の制約により自動設定できず・要手動設定）
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（2026-10-06 時点、`ls tests/unit` による）
- - Blocked by: #542（`pr_merge_gate` の撤去）、#538（Codex supervisor の撤去）。**この環境では依存関係を設定する手段がないため、未設定です。手動での設定が必要です。**
- | Horizon | `Next` | **オーナー確認済み（2026-10-06）**。#542・#538 の完了待ち |

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
