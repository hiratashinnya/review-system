# Issue #184「validate.py の TD-TC 1:1検証（exact_link_counts）が activate_stage を無視して常時発火し、段階的著作をブロックしうる」

- URL: https://github.com/hiratashinnya/review-system/issues/184
- 状態: closed（2026-11-18取得）
- 本文: 1072文字/ 20行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #147
- PR参照: #147
- 主見出し: ## 発見経緯 | ## リスク内容 | ## 深刻度 | ## 受け入れ基準 | ## 関連
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - 現状 TD/TC/SRC ノードは0件のため未発火＝潜在バグであり、「validate.py がエラー0件」という自己検証（Codexレビューが根拠にした検証コマンド）を通過してしまっている。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
