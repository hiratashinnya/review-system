**深刻度**: INFO
**内容**: アンブレラ SPEC-44 の `condition: normal` だが、子 SPEC-44-1 は `condition: normal`、SPEC-44-2 は `condition: boundary`（BOM 検出）、SPEC-44-3 は `condition: error`（デコードエラー）と多様である。傘の condition が normal 固定で子の condition 多様性を代表しておらず、形式上ミスリードを招く（傘は非テスタブルのため実害は低い）。同種の傘（複数 condition の子を束ねるアンブレラ）が他にも存在する（横断的論点）。一方、傘から condition を外すと RULE-016（SPEC は condition 必須）に抵触する。
**推奨**: 傘ノードの condition の意味づけ（代表 condition なのか、無効化マーカーなのか）を notation/規約で定義する。RULE-016 との両立のため、condition フィールドを残しつつ傘では `condition: normal`（または `mixed` 等の専用値）の意味を規約側で定義する解を検討する。
**対応内容**: DD「傘 SPEC は condition を省略し傘ロールを edges から機械判定」に従い、RULE-016 SPEC に傘ロール除外条件を明記し、同型 child→parent 辺から導出される傘 SPEC の残存 `condition` を省略へ統一した。config/FORMAT/notation/agent 資産にも、傘ロールは condition 値ではなく edges 由来で導出し RULE-016 対象外とする旨を明文化した。
**対応状況**: resolved（2026-07-08・Issue #78 follow-up）
**指摘時 ref_version**: SPEC-44 "0.2"（ノードバッジ x.y 基準・DD-8）
