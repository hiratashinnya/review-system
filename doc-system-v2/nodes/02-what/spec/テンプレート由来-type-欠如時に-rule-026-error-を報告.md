**前提条件**: テンプレート `templates/<layer>/<type>.md` の `type:` フィールドが削除されている、または空になっている（`id:` は存在する）。
**入力/トリガ**: 著者がその `type` 欠落テンプレートを複製してノードを著作し、検証ツールが当該ノードを処理する。
**期待動作**: テンプレート由来で `type` を欠くとき、RULE-026（type 欠如）の ERROR を報告する。
**例**: `templates/requirements/FR.md` の `type:` 行が削除 → 著者が複製して `doc-system/02-what/01-fr.md` 行14に著作（id は `FR-1`）→ `ERROR|doc-system/02-what/01-fr.md:14|RULE-026|FR-1|type field missing or empty`。
