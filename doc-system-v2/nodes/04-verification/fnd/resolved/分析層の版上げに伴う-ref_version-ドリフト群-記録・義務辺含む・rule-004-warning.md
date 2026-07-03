**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→VERIFY-1 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 VERIFY-1 から `→FND-17` の backward 辺を受ける（backref 付与）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: 分析層ファイルの版上げに下流の ref_version 更新が追随しておらず RULE-004 ドリフトが多発。
- (a) `01-actors.md` が 0.2→0.3（ACTOR-3 削除の x.y 上昇）したが、流入辺 E-1→ACTOR-1・E-2→ACTOR-1・O-1→ACTOR-2・O-2→ACTOR-2・VERIFY-1→ACTOR-1 が "0.2" のまま。
- (b) VERIFY-1 の I-1("0.4"→現0.6)・P-1("0.4"→現0.6)・E-1("0.4"→現0.5) が陳腐化。
- (c) 解消済み FND-2→P-2("0.5"→0.6)・FND-3→E-1("0.4"→0.5)・FND-4→P-3("0.5"→0.6)、義務辺 PEND-1→I-1-1("0.5"→0.6) がドリフト。
- (d) 付随：FND-3 の forward 辺が E-1 を指すが、当該指摘の処置（E-3→E-2 リネーム）の back-ref は E-2 に付与されており、forward/back の対象ノードが不一致（FND-3 は本来 E-2 を指すべき疑い）。

**対応状況**: resolved
**対応内容**: DD-4（decisions.md）として昇格し推奨案を実施。「生きた」依存辺（E-1/E-2→ACTOR-1・O-1/O-2→ACTOR-2 の ref_version "0.2"→"0.3"、FND-3 forward の E-1→E-2＋"0.5"、PEND-1→I-1-1 の "0.5"→"0.6"）を一括更新済み。凍結記録（VERIFY-1・解消済み FND-2/FND-4）は DD-2 決定（suppress[RULE-004]・再検証シグナル）に委ねる。処置対象ノードに `→DD-4` バックリファレンス付与済み。
**指摘時 ref_version**: VERIFY-1 "0.1"（doc-system/04-verification/01-doc-verify.md・VERIFY-1 ノードバッジ v0.1.1 時点・辺逆転で削除した元 forward 辺 `→VERIFY-1 "0.1"` の処置対象＝backref 付与先）
