**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺 `→SPEC-46`（ref_version "0.1"）を削除し `edges: []`・`resolved: true` を付与した。処置対象のテスタブル化分割後 SPEC（SPEC-46-1/46-2）から `→FND-69` の backward 辺を受けており、resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録済み（DD-3）。

**内容**: SPEC-46 の `**期待動作**` が、「外部参照パターンが非存在である」「0件を確認する」「検証を通過する」の複数動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。パターン非存在判定・件数確認・通過判定はそれぞれ別動作で、独立した検証単位とすべき。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14・→ SPEC-46-1/46-2）
**指摘時 ref_version**: SPEC-46 "0.1"（ノードバッジ x.y 基準・DD-8）
