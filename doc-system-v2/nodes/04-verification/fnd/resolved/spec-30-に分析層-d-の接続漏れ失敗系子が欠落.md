**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺 `→SPEC-30`（ref_version "0.1"）を削除し `edges: []`・`resolved: true` を付与した。処置対象 SPEC-30 から `→FND-87` の backward 辺を受けており、resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録済み（DD-3）。

**内容**: アンブレラ SPEC-30「分析ノードの接続漏れ検出」の子は SPEC-30-1（未駆動出力 O→P 欠如）/30-2（未定義反応イベント E←P 欠如）/30-3（未消費入力 I←P 欠如）の3種だが、分析層 D（内部データ）の接続漏れ（D→P・D←P 欠如）の失敗系子が欠落している。config の `must_link_to: D→P`・`must_be_linked_from: D←P` は RULE-006 対象であり、D の接続漏れも検出されるべき検査対象である。SPEC-8 一般則でカバーされる前提なら、SPEC-30 概要にその旨の明記がなく、検証カバレッジの穴か単なる暗黙包含かが読み取れない。
**推奨**: SPEC-30 に D 接続漏れの failure 子（SPEC-30-4）を追加するか、D は SPEC-8 一般則でカバーされる旨を SPEC-30 概要に明記する。要否（専用子の新設 vs 一般則委譲の明記）はオーナー判断。
**対応状況**: resolved（2026-06-15）
**処置**: 実カバレッジ穴ではない。SPEC-8 一般則（RULE-006）が D→P・P→D をカバーするため専用子は不要。SPEC-30 概要に「D は SPEC-8 でカバー・本傘はアクタ面 O/E/I のみ列挙」と設計意図を明記。spec-author が SPEC-30 に `→FND-87` バックリファレンス辺を付与済み。
**指摘時 ref_version**: SPEC-30 "0.1"（ノードバッジ x.y 基準・DD-8）
