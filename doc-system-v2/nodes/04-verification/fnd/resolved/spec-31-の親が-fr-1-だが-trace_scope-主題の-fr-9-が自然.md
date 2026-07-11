**深刻度**: INFO

**改訂理由（z バンプ v0.1.0→v0.1.1・Issue #159 対応）**:
SPEC-31 の親辺を FR-1 から FR-9 へ付け替え、本文に親辺根拠を明記した。DD-16 の fnd_lifecycle に従い、元 forward 辺 `→SPEC-31`（ref_version "0.1"）を削除し `edges: []` とした。処置対象 SPEC-31 から `→FND` の backward 辺を受けており、指摘時 ref_version は本文に保持する。

**内容**: SPEC-31（trace_scope 結果 in-graph 0件・empty）の親辺が `to: FR-1`（ノードグラフ構造化）になっている。しかし in-graph 集合の決定は FR-9（トレース対象集合の宣言・trace_scope）の主題であり、親は FR-9 が自然との議論余地がある。現状 SPEC-24-1/24-2 が FR-9 配下に置かれている。
**推奨**: SPEC-31 の親を FR-9 へ付け替えるか、FR-1 配下に留める根拠（パース正常系の境界＝empty）を本文に明記する。オーナー判断。
**対応状況**: resolved（FR-9 へ親辺付け替え・2026-07-11）
**指摘時 ref_version**: SPEC-31 "0.1"（ノードバッジ x.y 基準・DD-8）
