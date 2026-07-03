**前提条件**: エージェントが `id` フィールドを欠いたノードを tmp ファイルに出力済みである。
**入力/トリガ**: reconciliation が tmp ファイルの id 欠如を検出する。
**期待動作**: id 欠如を検出したとき、reconciliation は本ファイルへの転記を中断する（fail-close）。
**例**: tmp ファイルに `type: FR` のみで `id:` なし → reconciliation が `doc-system/02-what/01-fr.md` への転記を中断する。
