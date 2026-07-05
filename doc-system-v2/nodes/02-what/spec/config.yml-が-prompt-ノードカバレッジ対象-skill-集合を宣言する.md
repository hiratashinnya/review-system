**前提条件**: doc-system の設定ファイル `config.yml` が読み込み済みで、DD-22 が確定した PROMPT ノードカバレッジ対象 skill 集合（13 件）が定まっている。
**入力/トリガ**: 検査系（validate.py／spec-inspector）が `config.yml` から PROMPT ノードカバレッジの対象 skill 集合の宣言（in-graph ファイル宣言＝`trace_scope` と同一イディオムの宣言キー）を読み取る。
**期待動作**: `config.yml` が PROMPT ノードカバレッジ対象 skill 集合を**単一ソースとして宣言している**ことを判定する（`trace_scope` が in-graph ファイル集合を `config.yml` で宣言するのと同型に、対象 skill 集合を config で宣言する）。
**例**: `config.yml` の当該宣言キーに 13 件の対象 skill（工程別10＝align / value-trace / mvp-scope / schema-design / domain-model / architecture-design / orchestration-design / prompt-design / test-strategy / spec-principles、パイプライン3＝spec-pipeline / impl-design-pipeline / asset-pipeline）が列挙され、DD-22 が対象外とした 4 件（coverage-html / asset-lateral-deploy / agy-delegate / bloom-model-tier）は含まれない → 宣言充足。

- **provenance / 位置づけ**: 傘 SPEC-61（`対象 skill の LLM プロンプト資産を設計層 PROMPT ノードで在グラフモデル化`）の子。issue #63 の前提として、`config.yml`／RULE 変更を SPEC 駆動化する（config 変更は SPEC 先行・FND-102「必須辺 44 行を全 dedicated SPEC 化」／FND-103「fnd_lifecycle の RULE を dedicated SPEC 化」の慣行に倣う）。決定元＝DD-22（2026-07-01 オーナー確定・対象 skill 13 件を確定）。対象集合の宣言先を `config.yml` とするのは、`trace_scope` が in-graph ファイル集合を config で宣言するイディオムと同型（設定を単一ソースにし、対象を散在させない）。
- **姉妹 SPEC との関係**: 本 SPEC が宣言先を規定し、姉妹 SPEC「宣言された対象 skill 集合の PROMPT ノード欠落を機械検査で報告する」がその宣言集合を入力に欠落検査する（本 SPEC が宣言、姉妹 SPEC が消費）。
- **指摘時 ref_version（DD-3・辺を張る対象分）**: 傘 SPEC-61 "0.1"（親 SPEC→SPEC 辺・`対象-skill-の-llm-プロンプト資産を設計層-prompt-ノードで在グラフモデル化` 現バッジ v0.1.0 時点＝x.y "0.1"）。
