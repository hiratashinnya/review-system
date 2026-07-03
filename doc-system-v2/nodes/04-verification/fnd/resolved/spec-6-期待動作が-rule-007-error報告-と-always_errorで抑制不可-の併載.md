**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺 `→SPEC-6`（ref_version "0.2"）を削除し `edges: []`・`resolved: true` を付与した。処置対象のテスタブル化分割後 SPEC（SPEC-6-1/6-2）から `→FND-44` の backward 辺を受けており、resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録済み（DD-3）。

**内容**: SPEC-6 の `**期待動作**` が、「RULE-007 で ERROR を報告する」という検証動作アサーションに加えて、「always_error のため抑制不可」という抑制可否の独立文を併載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。検証動作の検証と抑制不可性の検証は別目的語・別条件であり1ノードに混在させるべきでない。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ SPEC-6-1/6-2
**指摘時 ref_version**: SPEC-6 "0.2"（ノードバッジ x.y 基準・DD-8）
