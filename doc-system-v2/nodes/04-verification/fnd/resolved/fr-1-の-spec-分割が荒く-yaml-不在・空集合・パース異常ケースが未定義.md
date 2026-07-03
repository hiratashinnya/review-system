**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→FR-1 "0.3"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 FR-1 から `→FND-12` の backward 辺を受けており、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録（DD-3）。

**内容**: FR-1（ノードグラフの構造化表現）配下の SPEC は正常パース（SPEC-1）と崩れた記法（旧 SPEC-2）のみで、(a) in-graph 0 件の空集合、(b) ⬡ マーカー直後に YAML ブロックが無い、(c) id 欠如、(d) type 欠如、(e) 辺の ref_version 欠如、といった等価分割クラスが未定義だった。パース段階の異常系（fail-close 対象）が仕様化されておらず、テスト設計の網羅軸が欠落していた。
**対応状況**: resolved
**対応内容**: パース検証 RULE-023〜027 を新設（docs/doc-system/05-verification.md 段階0・config 反映）。FR-1 配下に SPEC-31（empty・in-graph 0 件）・SPEC-32（RULE-024）・SPEC-33（RULE-025）・SPEC-34（RULE-026）・SPEC-35（RULE-027）を追加し、SPEC-2 を RULE-023 限定に書き直した（spec.md v0.3.0→0.3.1）。FR-1 に `→FND-12` バックリファレンス辺を付与済み（reconciliation が付与）。
**指摘時 ref_version**: FR-1 "0.3"（doc-system/02-what/01-fr.md v0.3 時点）
