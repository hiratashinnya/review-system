# Issue #366「[調査設計] 版リテラル追従漏れの機械検査 — 検査対象・判定規則・誤検出方針・実装場所を決める」

- URL: https://github.com/hiratashinnya/review-system/issues/366
- 状態: open（2026-11-18取得）
- 本文: 2579文字/ 60行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 5件（未チェック: 5）
- Issue参照: #365, #364, #367, #363, #345
- PR参照: #364
- 主見出し: ## 目的 | ## なぜ実装より先に設計を分けるか | ## Scope（決めるべきこと） | ### 既存の前例から学べること（調査の出発点。結論ではない） | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues | ## 起票先の分類について
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - **`tests/unit/test_governance_sync.py`** — `CLAUDE.md` と配送用の写しのハッシュ不一致を CI で fail-close に検知する。**フックが fail-open な nag でも、テストが赤くなるので merge 前に必ず露見する**という二段構えの前例

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
