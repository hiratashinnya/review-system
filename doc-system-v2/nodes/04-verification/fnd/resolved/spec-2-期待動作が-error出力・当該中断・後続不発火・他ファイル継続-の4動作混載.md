**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺 `→SPEC-2`（ref_version "0.3"）を削除し `edges: []`・`resolved: true` を付与した。処置対象のテスタブル化分割後 SPEC（SPEC-2-1/2-2/2-3/2-4）から `→FND-41` の backward 辺を受けており、resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録済み（DD-3）。

**内容**: SPEC-2 の `**期待動作**` が、「ERROR を出力する」「当該ファイルの処理を中断する」「後続 RULE-024〜027 を発火させない」「他ファイルの処理を継続する」の4動作を1ノードに混載しており、テスタブル基準（単一条件→単一目的語→単一動詞）に違反する。fail-close の副作用（中断・継続）も独立アサーションとして許容しない方針（オーナー方針 2026-06-14）に反する。
**推奨**: 1アサーション1SPEC で分割（-N 枝番）し、各 SPEC の期待動作を単一条件→単一動作に書き直す。
**対応状況**: resolved（テスタブル化分割・2026-06-14）→ SPEC-2-1/2-2/2-3/2-4
**指摘時 ref_version**: SPEC-2 "0.3"（ノードバッジ x.y 基準・DD-8）
