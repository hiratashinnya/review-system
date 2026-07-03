**前提条件**: `config.yaml` に `current_stage` が設定され、その値が `stages` に存在しない
**入力/トリガ**: ステージ発火判定（`index(current_stage)` の比較）を要求される
**期待動作**: `current_stage` 値が `stages` に存在しないとき、ステージ発火判定（index 比較）をスキップする
**例**: index(current_stage) が解決できないため、発火ステージとの大小比較は実行されない
