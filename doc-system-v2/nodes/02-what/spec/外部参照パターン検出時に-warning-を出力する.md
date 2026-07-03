**前提条件**: スキルファイルが1件以上存在し、全行が外部参照パターンで検索済みである。
**入力/トリガ**: asset-auditor が外部参照パターンにマッチする行を1件以上検出する。
**期待動作**: 外部参照パターンにマッチする行を検出したとき、当該行を指す WARNING を1件出力する。
**例**: `.claude/skills/spec-author/SKILL.md` 行42に `see: ../07-authoring-guide.md` が存在 → `WARNING|.claude/skills/spec-author/SKILL.md:42|NFR-3-check|(none)|external file reference: ../07-authoring-guide.md` を出力。
