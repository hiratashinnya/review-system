**前提条件**: FR-17 が定める対象 skill 集合（13 件）が定義済みで、doc-system の PROMPT 型ノード群が読み込み済みである。
**入力/トリガ**: spec-inspector（検査系）が対象 skill 集合の各 skill 名について、対応する設計層 PROMPT ノードを在グラフから探索する。
**期待動作**: 対象 skill 集合の各 skill について、その機能を束ねた PROMPT 型ノードが在グラフに1件以上存在することを判定する。
**例**: skill `spec-pipeline` に対応する `type: PROMPT` ノードが doc-system に存在 → 存在充足。対象集合外の `bloom-model-tier` は探索対象に含めない。
