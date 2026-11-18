# Issue #581「asset_parity の staleness flags（27 件）と mirror orphans（3 件）の扱いを調査する」

- URL: https://github.com/hiratashinnya/review-system/issues/581
- 状態: closed（2026-11-18取得）
- 本文: 5853文字/ 100行。全文: `../raw/issues-2026-10.jsonl`
- AC: 6件（未チェック: 0）
- Issue参照: #542, #729, #730, #468, #41472663048, #418, #617, #637
- PR参照: なし
- 主見出し: ## 目的と起票時の状況（履歴） | ## 2026-11-03 最新実測 | ## 起票時staleness 27件の個別分類 | ## orphan 3件の個別分類 | ## 選択肢の比較と結論 | ## Acceptance criteria（調査として完了） | ## Dependencies / Related
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - stalenessのうち **27ペア** が本Issue対象。残り2ペアの `issue-pipeline` は #468 に分離（#468は現在CLOSED）。
- - 27件という数値は起票時の履歴であり、現在の総件数を表すものではない。
- | Asset / mirror | 現行理由・現在の状態 |
- 2. **#730** — 文書化された3件のmirror-onlyを未分類orphanと区別する。#729との論理的なblocked-byはなし。ただし `report_text.py` / `report_json.py` / テストが重なるため、実装順は #729 → #730 推奨。
- - **後続:** #729、#730（両方OPEN）
- - Blocked by: なし

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
