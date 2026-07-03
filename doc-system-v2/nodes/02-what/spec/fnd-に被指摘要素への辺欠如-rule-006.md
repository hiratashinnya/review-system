**前提条件**: 型が FND の未解消ノード（`resolved: false` / 未設定）が存在する（verification ステージ）
**入力/トリガ**: 未解消 FND に指摘対象要素への forward 辺がない（`fnd_lifecycle.unresolved.must_link_to`・target: any・severity error。DD-16・Q-4 で `must_link_to` 標準セクションから状態依存ルールへ移管）
**期待動作**: RULE-006 ERROR を報告する（config reason「RULE-006 後継」・旧 RULE-009）
