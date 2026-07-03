ノード型ごとに、その配下 SPEC が満たすべき condition の必須・推奨集合を定義するカバレッジ要件の実インスタンス。RULE-017（required 欠落＝WARNING）・RULE-018（recommended 欠落＝WARNING）の判定基準となる。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `coverage_rules:` 配下。`FR.required_conditions: [normal]`・`FR.recommended_conditions: [failure, error]`。
