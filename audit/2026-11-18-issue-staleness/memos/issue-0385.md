# Issue #385「gated ロールが AC 必須の検証コマンド（asset_parity/time_fixture_lint）を層2 allowlist の穴で実行できない」

- URL: https://github.com/hiratashinnya/review-system/issues/385
- 状態: closed（2026-11-18取得）
- 本文: 4802文字/ 104行。全文: `../raw/issues-2026-08b.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #356, #372, #129, #350, #353, #305, #155
- PR参照: #353
- 主見出し: ## 目的・背景 | ## 現状と根拠（実測） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## Project fields（提案・要オーナー確認）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- ## 現状と根拠（実測）
- （`agent-command-gate.sh: PreToolUseフィールド名未検証(fail-open)＋正規表現の回避手段・誤検知バグ`・CLOSED）
- - `agent-command-gate.sh` の fail-open/fail-close 挙動そのものの再設計（#129 の既存スコープ）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
