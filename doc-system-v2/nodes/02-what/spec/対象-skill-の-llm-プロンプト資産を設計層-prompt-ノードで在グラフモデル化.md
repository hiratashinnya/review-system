**概要**: FR-17「skill の LLM プロンプト資産モデリング（機能軸）」を検証可能アサーションに落とす傘ノード（非テスタブル）。doc-system の価値実現に直結する対象 skill（14 件）を、**何をする prompt かという機能で束ねた設計層 PROMPT ノード**として在グラフに表現するという要件を、次の3つのテスタブルな子 SPEC に分けて検証する：PROMPT ノードの存在（SPEC-61-1）／傘 SPEC-61 への親辺（SPEC-61-2）／キャリア属性 skill｜agent の保持（SPEC-61-3）。

- **対象 skill 集合（14 件）**: 工程別10＝align / value-trace / mvp-scope / schema-design / domain-model / architecture-design / orchestration-design / prompt-design / test-strategy / spec-principles、パイプライン3＝spec-pipeline / impl-design-pipeline / asset-pipeline、境界IN 1＝docidx（retrieval が VAL-1 を支援するため DD-22 で既定 IN）。対象外4件（coverage-html / asset-lateral-deploy / agy-delegate / bloom-model-tier）は NFR-3／SPEC-46 の検査対象アーティファクトのままとし、本 SPEC の対象集合に含めない。

- **既存 PROMPT 型の流用（新ノード型を起こさない）**: 本軸の skill PROMPT ノードは既存の設計層 PROMPT 型を流用する。著作エージェント PROMPT（SPEC-27 系＝PROMPT-1〜7・`to: SPEC-27`）と本軸の skill PROMPT（`to: SPEC-61`）は**目的で区別される別軸**だが、いずれも同一の PROMPT 型ノードであり、辺先（SPEC-27 か SPEC-61 か）で識別される（SPEC-61-2 の親辺検査がこの識別を担保する）。新規ノード型は導入しない。

- **キャリア属性は届け方であり要件軸を分けない**: skill か agent かは PROMPT の届け方を表すキャリア属性にすぎず、機能軸（本 SPEC）を分割しない。将来 skill→agent 変換（DD-22 ①-C の非対話 fan-out のみ orchestrator agent 化）が起きても、PROMPT ノードはキャリア属性＋版の変更で表し、別 SPEC 軸へ付け替えない（churn 回避）。

- **provenance**: 決定元＝DD-22（2026-07-01 オーナー確定・Q-6 から昇格。②-A「skill を PROMPT 型流用で在グラフモデル化」の要件化 FR-17 を SPEC 化）。価値根拠は VAL-3（著作効率）＋ VAL-1（トレーサビリティ）／VAL-4（段階的前進）で、親 FR-17→SR-1 経由で到達する（VAL への直接辺は張らない・PR9）。

- **接続規則（config.yaml）は変更しない**: 子 SPEC が判定する「skill PROMPT ノード → 傘 SPEC」の辺は既存の `must_link_to: {node: PROMPT, target: SPEC}` 規則の適用範囲であり、本 SPEC 著作で config.yaml の接続規則・RULE は一切変更しない（PROMPT→SPEC は既存規則で成立）。

- **検査 RULE の新設要否は本 SPEC で詰めない（FND/Q 候補）**: 対象 skill 集合に対する PROMPT ノードの存在（SPEC-61-1）・親辺（SPEC-61-2）・キャリア属性（SPEC-61-3）を spec-inspector が機械判定するための新しい検査 RULE／config スキーマ（対象 skill 集合の宣言先・carrier 属性の語彙定義）が必要かは、本 SPEC では確定しない。実 skill PROMPT ノード 14 件の著作、carrier 属性のスキーマ化、必要な検査 RULE 新設は別途 FND/Q で起票して判断を仰ぐ（PR7・独断で config を変更しない）。

- **指摘時 ref_version の記録（DD-3・辺を張る対象分）**: FR-17 "0.1"（02-what/03-spec.md 側 SPEC→FR 辺・FR-17 現バッジ v0.1.0 時点＝x.y "0.1"）。

- **親 FR-17 の更新**: FR-17 は子への辺を持たない（階層は ID／SPEC→FR 辺から推論）。FR-17 は本 SPEC-61 からの被参照（`must_be_linked_from: {node: FR, source: [SPEC]}` WARNING）を SPEC-61→FR-17 辺で充足するため、FR-17 側の追加編集は不要。
