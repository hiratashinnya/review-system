**前提条件**: テンプレート `templates/<layer>/<type>.md` の `id:` フィールドが削除されている、または空になっている。
**入力/トリガ**: 著者がその `id` 欠落テンプレートを複製してノードを著作し、検証ツールが当該ノードを処理する。
**期待動作**: テンプレート由来で `id` を欠くとき、RULE-025（id 欠如）の ERROR を報告する。
**例**: `templates/requirements/FR.md` の `id:` 行が削除 → 著者が複製して `doc-system/02-what/01-fr.md` 行14に著作 → `ERROR|doc-system/02-what/01-fr.md:14|RULE-025|(none)|id field missing or empty`。
