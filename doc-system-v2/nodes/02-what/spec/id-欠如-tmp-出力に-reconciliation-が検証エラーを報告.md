**前提条件**: エージェントが `id` フィールドを欠いたノードを tmp ファイルに出力済みである。
**入力/トリガ**: reconciliation が tmp ファイルを検証し、id フィールドの欠如を検出する。
**期待動作**: id 欠如を検出したとき、reconciliation は検証エラーを報告する。
**例**: tmp ファイルに `type: FR` のみで `id:` なし → reconciliation が検証エラーを報告する。
