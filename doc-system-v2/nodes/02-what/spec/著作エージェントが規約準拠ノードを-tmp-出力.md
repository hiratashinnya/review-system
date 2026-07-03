**前提条件**: `.claude/agents/` に型別著作エージェント定義（例 `requirements-author.md`）が存在し、著者が FR 著作を依頼する。
**入力/トリガ**: 著者が `requirements-author` エージェントに FR ノード1件の著作を依頼する。
**期待動作**: 著者が著作を依頼したとき、エージェントは `type: FR`・`id: FR-N`（連番）・`edges: [{to: SR-*, ref_version: "..."}]`・本文4項目を含むノードを `tmp/sprint-1/<parent-id>.md` に出力する。
**例**: `requirements-author` に「FR-13 著作」を依頼 → `tmp/sprint-1/fr-11-13-14.md` に `id: FR-13, type: FR, edges: [{to: SR-1, ref_version: "0.2"}]` ＋4項目本文が出力される。
