**前提条件**: エージェントが `id` フィールドを欠いたノードを tmp ファイルに出力済みで、reconciliation が検証フェーズで RULE-025 相当チェックを実施する。
**入力/トリガ**: reconciliation が tmp ファイルの id 欠如を検出する。
**期待動作**: id 欠如を検出したとき、reconciliation は `ERROR|{file}:{line}|RULE-025|(none)|id field missing or empty` を出力する。
**例**: tmp ファイルに `type: FR` のみで `id:` なし → `ERROR|tmp/sprint-1/fr-11-13-14.md:5|RULE-025|(none)|id field missing or empty` を出力する。
