**前提条件**: `config.yaml` に `current_stage` が設定されている
**入力/トリガ**: `stages` リストに `current_stage` 値が存在しない
**期待動作**: `current_stage` 値が `stages` に存在しないとき、ツール設定エラーを報告する
**例**: current_stage=`reqirements`（誤記）が stages に無いとき、設定エラー1件が出力される
