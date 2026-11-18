# Issue #164「out-of-graph著作資産伝播FNDのbackref対象を在グラフ化してcloseする」

- URL: https://github.com/hiratashinnya/review-system/issues/164
- 状態: closed（2026-11-18取得）
- 本文: 492文字/ 18行。全文: `../raw/issues-2026-07a.jsonl`
- AC: 0件（未チェック: 0）
- Issue参照: なし
- PR参照: なし
- 主見出し: なし
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - open FND「設計接続規則の決定（FND-96・DD-15）が out-of-graph 著作資産に未伝播」は、本文上 resolved とされている一方、backref 対象ノードが未著作のため open に残っている。
- - Sprint 1 では、明示 defer されていない FND は open のまま残さない。
- - 当該 FND が `fnd/open` から消える。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
