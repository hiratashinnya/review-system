# Issue #344「main の赤を merge 前に止める：PR で unit test 全体スイートを回す＋時刻依存 test data の再発防止」

- URL: https://github.com/hiratashinnya/review-system/issues/344
- 状態: closed（2026-11-18取得）
- 本文: 5556文字/ 108行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 10件（未チェック: 10）
- Issue参照: #339, #335, #302, #322, #316
- PR参照: #335, #322, #316
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 穴1: PR にテストの status check が無い | ### 穴2: 時刻依存 test data が同一クラスで2度目 | ### 無課金で実現できる | ## Scope | ### 手当てA: PR で全体スイートを回す | ### 手当てB: 時刻依存 test data の再発防止 | ## Out of scope | ## Acceptance criteria | ### 手当てA | ### 手当てB
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - **1度目 = #302**（2026-08-04 closed）。`tests/unit/test_codex_rate_limit_api.py` の固定 epoch `1783767886` が時間窓外になりテストが失敗。AC に「**fixed epoch と現在時刻の偶発的な相対関係に依存する test data が残っていない**」が含まれていた。
- - **現在の状態**: `83724a4`（PR #322）が `test_blocker_gate_contract_cli.py` 側で `blocker_gate.resolver.datetime` の `now` を `2026-08-02` に固定したため**防御済み**。ただし **fixture の絶対日付そのものは残っており**、同 fixture を clock 固定せずに使う新規テストを書けば**再武装する**。
- | **Priority** | `P2` | `P2`＝通常。`main` は現在 green（`83724a4` で解消済み）で即時対応が必要な重大障害ではないため `P0`/`P1` は当たらない。一方で PR にテスト gate が無い状態は継続リスクであり、`P3`（低緊急度）には下げない |
- - Blocked by: なし

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
