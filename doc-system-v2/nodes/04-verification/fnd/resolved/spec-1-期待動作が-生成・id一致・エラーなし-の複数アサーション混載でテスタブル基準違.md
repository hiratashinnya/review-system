**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺 `→SPEC-1`（ref_version "0.3"）を削除し `edges: []`・`resolved: true` を付与した。処置対象のテスタブル化分割後 SPEC（SPEC-1-1/1-2/1-3）から `→FND-40` の backward 辺を受けており、resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録済み（DD-3）。

**内容**: SPEC-1 の `**期待動作**` が、テスタブル基準「`【条件】のとき、〇〇を▲▲する`（単一条件→単一目的語→単一動詞）」に違反し、「ノード1件を生成する」「PREFIX-N と id が一致する」「エラーを出力しない」の3アサーションを1ノードに混載している。1ノード=1判定にならず、TR の PASS/FAIL がどのアサーションに対するものか曖昧になる。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ SPEC-1-1/1-2/1-3
**指摘時 ref_version**: SPEC-1 "0.3"（ノードバッジ x.y 基準・DD-8）
