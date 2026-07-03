属性検査ルール（接続辺以外の RULE）ごとに、発火を開始するステージを定義する写像。current_stage が指定ステージ未満の間は当該ルールを発火させない（段階ゲート）。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `rule_activation:` 配下。`RULE-016/017/018: requirements`（condition 属性・FR カバレッジ系）・`RULE-019/020/021: verification`（TD↔SPEC 不一致・TR result/log_ref 欠落）。
