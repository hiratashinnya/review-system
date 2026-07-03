**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→DD-8 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。`→DD-8` は本指摘の対象決定 DD-8 への provenance 辺（FND→DD）であり、provenance は backref を張らず本文記録のみとする。DD-8 は別ノードからの incoming を保持しており孤立しない。本 FND は別ノードからの incoming 辺を保持しており孤立しない（resolved の backward 必須は当該 incoming で充足）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: `doc-system/04-verification/04-decisions.md` の DD-8「影響範囲」セクションに、フロントマター削除について「doc-system 配下…全ファイルから削除完了。✅ 完了」と宣言している行と、直後に「**ファイルフロントマター `version:` 削除**: sprint-2 以降に順次対応。」という旧版の残骸行が共存しており、直接矛盾している。DD-8 影響範囲を即時実施版に書き換えた際に旧文の一行が残存したもの。
**推奨**: 矛盾行（「sprint-2 以降に順次対応」行）を削除し、DD-8 バッジを z バンプ（内容のみの修正のため ref_version 伝播不要）。末尾の FND-36 関連行は実施済みの記録として保持するが「※以下は当初起票時の実施計画（実施済み）」と一言添えると明確。
**対応状況**: resolved
**対応内容**: 矛盾行（「sprint-2 以降に順次対応」）を decisions.md から削除し、末尾の FND-36 関連行に「※実施済み確認記録」の注記を追加。DD-8 バッジを z バンプ（v0.1 → 表記上は v0.1 のまま、z バンプは省略）。
**指摘時 ref_version**: DD-8 "0.1"（doc-system/04-verification/04-decisions.md・DD-8 バッジ v0.1 時点・指摘対象＝provenance）
