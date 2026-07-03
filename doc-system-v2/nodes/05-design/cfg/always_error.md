いかなる抑制機構（scheduled / suppress / activate_stage）によっても抑制できない RULE の一覧。グラフ整合性の根幹に関わるため常に error として発火させる fail-close 指定。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `always_error: [RULE-005, RULE-007]`。RULE-005＝完全孤立（in/out 辺が0本）、RULE-007＝存在しない ID 参照。
