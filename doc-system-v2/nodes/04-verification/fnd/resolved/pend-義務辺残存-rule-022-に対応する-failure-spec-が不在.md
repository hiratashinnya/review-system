**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺 `→FR-5`（ref_version "0.2"）を削除し `edges: []`・`resolved: true` を付与した。処置対象 SPEC-55（FR-5 配下に新設した PEND 義務辺残存 failure SPEC）から `→FND-80` の backward 辺を受けており、resolved ルール（backward 必須・forward 不在期待）を満たす。指摘の親要件 FR-5 側への backref 追加（FR-5 → FND-80）は reconciliation の所掌で付与する。指摘時 ref_version は本文に記録済み（DD-3）。

**内容**: FR-5 配下に DD 義務辺残存＝SPEC-12（RULE-001）・Q 義務辺残存＝SPEC-13（RULE-002）はあるが、PEND 義務辺残存（RULE-022 WARNING）を検証する failure SPEC が存在しない。decision_spine の3型（DD/Q/PEND）のうち PEND だけカバレッジが欠落しており、PEND の義務辺残存が検証鎖から漏れている。
**推奨**: FR-5 配下に PEND 義務辺残存（RULE-022）の failure SPEC を新設（SPEC-12/13 と同型）。要否はオーナー確認。
**対応状況**: resolved（2026-06-15）
**処置**: FR-5 配下に SPEC-55「PEND の義務辺残存（failure）」（RULE-022 WARNING・SPEC-12/13 同型）を新設し、decision_spine 3型（DD/Q/PEND）の義務辺残存カバレッジの対称を回復。spec-author が SPEC-55 に `→FND-80` バックリファレンス辺を付与済み。
**指摘時 ref_version**: FR-5 "0.2"（ノードバッジ x.y 基準・DD-8）
