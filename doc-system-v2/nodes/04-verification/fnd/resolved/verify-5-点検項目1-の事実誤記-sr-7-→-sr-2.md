**深刻度**: INFO

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→VERIFY-5 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 VERIFY-5 から `→FND-34` の backward 辺を受けており、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録（DD-3）。

**内容**: VERIFY-5（doc-system/04-verification/01-doc-verify.md）の点検項目1に「FR-15/16 → SR-7 辺あり ✓」と記載されているが、FR-15・FR-16 の実際の辺はいずれも `to: SR-2`（単一 CLI エントリポイント）であり、SR-7（フェーズ・ステージ進行に応じた検査ノイズ制御）は参照していない。`tmp/doc-system/verify5.md` にも同じ誤記がある。事実誤記であり、PASS 判定（FR→SR 接続あり ✓）自体は正しい（FR-15/16 が SR への接続を持つこと自体は事実のため、結論は不変）。
**推奨**: doc-verify.md と tmp/verify5.md の「SR-7」を「SR-2」に修正し、doc-verify.md を z-bump（v0.1.5→v0.1.6）。再走査不要（結論不変）。
**対応状況**: resolved
**対応内容**: doc-verify.md（v0.1.6）と tmp/verify5.md の点検項目1を SR-2 に修正。VERIFY-5 は suppress[RULE-004] の凍結スナップショットだが、事実誤記の訂正は版内修正として実施。バックリファレンス辺は VERIFY-5 に `→FND-34` を付与（suppress 付き凍結ノードだが訂正記録として）。
**指摘時 ref_version**: VERIFY-5 "0.1"（doc-system/04-verification/01-doc-verify.md v0.1.5 時点）
