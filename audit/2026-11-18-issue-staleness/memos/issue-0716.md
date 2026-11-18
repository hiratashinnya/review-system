# Issue #716「GitGate の base 取り込みで PR base.sha と現在のブランチ先端の不一致を扱う」

- URL: https://github.com/hiratashinnya/review-system/issues/716
- 状態: closed（2026-11-18取得）
- 本文: 1084文字/ 22行。全文: `../raw/issues-2026-11.jsonl`
- AC: 4件（未チェック: 4）
- Issue参照: #682, #600, #706, #712, #704
- PR参照: #682, #712
- 主見出し: ## 問題 | ## 目的 | ## 受け入れ条件 | ## 関連
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- PR #682 の base 取り込みにおいて、GitHub の PR API が返す `base.sha` は `06275f514985de6a975fa2f723c0596a821c145b`、現在の `main` と fresh fetch の先端は `29b8d474304f3b62677b3be84397c9fbbe49edea` だった。`gitgate/base_live.py` は `--expected-base` と PR API の
- この一致条件は #600 由来で、#706 の実装 PR #712 でも残っている。既存テストは両値が等しい前提か差異の拒否を検証しており、base が進んだ状態を検証していない。
- OPEN PR の実際の base ブランチの最新先端を head に取り込めるようにする。PR API の `base.ref`・repository・head を確認し、現在の base 先端は適切な live branch 情報と fresh fetch を照合する。PR API の `base.sha` が先端と異なるだけで拒否しない。開始から続行まで、head、base、PR の付け替えや操作中の意図しない変更の検出は維持する。
- - [ ] PR API の base.sha が旧値でも、現在の base ブランチ先端が live 情報と fresh fetch で一致する場合に正常取り込みと conflict 解消・続行ができる。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
