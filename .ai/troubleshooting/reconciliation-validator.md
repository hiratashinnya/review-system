# reconciliation-validator — 回復手順（非規範）

ROLLBACK になったら tmp の著作物を消去・自己修正せず、errors の対象 slug、参照先、field、期待状態を呼び出し元へ返す。著作側が修正した後に同じ parent 集合で再検証する。self_fix は target、field、確定値が揃う場合だけ適用候補として返し、値を推測して VALIDATION_OK に変えてはならない。

parent 集合や update_slugs の不一致があれば、欠けた親だけを成功扱いにせずバッチ全体を ROLLBACK とする。既存更新の宣言漏れは著作側で hand-off を修正し、検証器側で corpus の存在から補わない。
