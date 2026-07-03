DD / Q / PEND の決定スパイン義務辺ルールの実インスタンス。これらのノードから対象への辺が存在する＝反映未完了を意味し、反映後に辺を削除して逆向き（X → DD）に張り替える運用を機械検査する。義務辺にも ref_version が必須。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `decision_spine:` 配下。`{ node: DD, rule: RULE-001, severity: error }`・`{ node: Q, rule: RULE-002, severity: warning }`・`{ node: PEND, rule: RULE-022, severity: warning }`。
