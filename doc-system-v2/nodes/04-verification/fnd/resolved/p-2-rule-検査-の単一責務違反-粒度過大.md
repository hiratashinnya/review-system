**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→P-2 "0.2"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 P-2 から `→FND-2` の backward 辺を受けており、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録（DD-3）。

**内容**: P-2 が構造完結性（RULE-005〜008）・ドリフト（RULE-001/002/004/022）・カバレッジ（RULE-016〜019）・検証層（RULE-006/020/021）の全 RULE 群を1プロセスに内包している。対応 SPEC が SPEC-5〜23 と多数に分かれているのに、P-2 だけがそれらを束ねており、DFD レベリング上の単一責務の疑いがある。
**対応状況**: resolved
**対応内容**: DFD レベリングにより P-2 を P-2-1（ドリフト・義務辺）・P-2-2（構造完結性）・P-2-3（カバレッジ属性）・P-2-4（検証層完結性）の4子プロセスへ分解した（processes.md v0.4→0.5）。P-2 に `→FND-2` バックリファレンス辺を付与済み。
**指摘時 ref_version**: P-2 "0.2"（doc-system/03-analysis/03-processes.md v0.2 時点）
