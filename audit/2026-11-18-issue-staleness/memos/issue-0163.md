# Issue #163「current_stageに応じたimplementation/verification必須接続gateを実装する」

- URL: https://github.com/hiratashinnya/review-system/issues/163
- 状態: closed（2026-11-18取得）
- 本文: 803文字/ 20行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: #152
- PR参照: なし
- 主見出し: なし
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - しかし現状の `validate.py` は current_stage に応じて `must_link_to` / `must_be_linked_from` を全面評価していない。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
