# reconciliation-validator — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/reconciliation-validator.md`](../agents/reconciliation-validator.md) にある。

validator を read-only とし、自己修正を確定値付きの指示だけに限定するのは、著作・検証・本反映を単一ロールへ混ぜないためである。ROLLBACK は著作側へ戻し、reconciliation は `VALIDATION_OK` だけを受けることで、検証中の推測変更が正本へ流れない。

全 parent を一つの結果へ束ねる契約は、バッチの一部だけが成功した状態を呼び出し元が成功と誤認しないために必要である。既存更新の `update_slugs` を著作側の明示に限定するのも、validator がコーパスの存在だけから新規／更新を推測しない fail-close 境界を保つためである。
