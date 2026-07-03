doc-system の価値実現に直結する skill（工程別・パイプラインの LLM プロンプト資産）を、**何をする prompt かという機能で束ねた設計層 PROMPT ノード**として在グラフにモデル化し、著作効率・トレーサビリティ・段階的前進を支える LLM プロンプト資産を上流要件から辿れるようにする。

この軸は既存 FR-13（`*-author`／reconciliation 系＝著作エージェントと層ワークフロー。SPEC-27 が支える）とは**目的で区別される別軸**である。FR-13 が「著作エージェントが外部参照なしに規約を内包する」ことを扱うのに対し、本 FR は「doc-system の価値を生む skill 群を LLM プロンプト設計資産として在グラフ表現する」ことを扱う。

軸は **skill か agent かという届け方（キャリア属性）ではなく「機能」で束ねる**。skill→agent 変換（DD-22 ①-C の非対話 fan-out のみ orchestrator agent 化）が将来起きても、PROMPT ノードはキャリア属性＋版の変更で済み、要件軸の付け替え（churn）が起きない。対象は doc-system の価値実現に必要な skill 13 件（工程別 10：align / value-trace / mvp-scope / schema-design / domain-model / architecture-design / orchestration-design / prompt-design / test-strategy / spec-principles ＋パイプライン 3：spec-pipeline / impl-design-pipeline / asset-pipeline）。対象外 4 件（coverage-html / asset-lateral-deploy / agy-delegate / bloom-model-tier）は NFR-3／SPEC-46 の検査対象アーティファクトのままとする。既存の NFR-3（skill は self-contained）／SPEC-46（skill 自己完結の WARNING 検査）は不変で、その上に本 PROMPT モデル軸を**追加**で載せる（検査軸と設計モデル軸は両立）。

**provenance**:
- **決定元**: DD-22（2026-07-01 オーナー確定・Q-6 から昇格。②-A「skill を PROMPT 型流用で在グラフモデル化・新要件軸を新設」の要件化。本 FR は DD-22 由来）。
- **価値根拠**: VAL-3「著作効率＝工程別スキルが著作規約を内包」（あわせて VAL-1 トレーサビリティ・VAL-4 段階的前進に資する）。VAL への辺は張らず（FR→SR→VAL のレベリング＝PR9）、親 SR-1 経由で VAL-3 に到達する。

**指摘時 ref_version の記録（DD-3・辺を張る対象分）**:
- SR-1 "0.1"（01-why/02-sr.md SR-1 現バッジ v0.1.0 時点・親 SR）
- DD-22 "0.1"（04-verification/04-decisions.md DD-22 現バッジ v0.1.0 時点・決定元 provenance／decided のため backward 参照 X→DD として付与）
