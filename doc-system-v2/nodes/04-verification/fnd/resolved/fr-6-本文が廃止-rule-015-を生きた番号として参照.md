**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→FR-6 "0.2"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 FR-6 から `→FND-5` の backward 辺を受けており、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録（DD-3）。

**内容**: FR-6 本文は「TD の verifies 欠如（RULE-015）」を現役ルールとして記載するが、正本では RULE-015 は廃止され `must_be_linked_from: SPEC←[TD]`（RULE-006）に吸収済みである（docs/doc-system/05-verification.md L74・spec.md SPEC-15-1 は正しく「旧 RULE-015」と記述）。FR-6 のみ記述が旧モデルに取り残されている。
**対応状況**: resolved
**対応内容**: FR-6 本文の「TD の verifies 欠如（RULE-015）」を「SPEC への TD 被依存辺欠如（`must_be_linked_from: SPEC←[TD]`・RULE-006・旧 RULE-015）」へ修正した（fr.md）。FR-6 に `→FND-5` バックリファレンス辺を付与済み。
**指摘時 ref_version**: FR-6 "0.2"（doc-system/02-what/01-fr.md v0.2 時点）
