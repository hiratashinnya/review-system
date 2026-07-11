**深刻度**: INFO

**改訂理由（z バンプ v0.1.0→v0.1.1・Issue #159 対応）**:
SPEC-9-1 と SPEC-10 は統合せず、責務境界を本文へ明記した。SPEC-9-1 は既存依存辺の `ref_version` 不一致を failure として検出する責務、SPEC-10 は x.y 上昇を契機に再検査・再反映促しへ接続する normal 系 umbrella と位置づける。DD-16 の fnd_lifecycle に従い、元 forward 辺 `→SPEC-10`（ref_version "0.2"）を削除し `edges: []` とした。処置対象 SPEC-9-1/SPEC-10 から `→FND` の backward 辺を受けており、指摘時 ref_version は本文に保持する。

**内容**: SPEC-9-1（依存辺ドリフト・failure）と SPEC-10（ファイル/ノード x.y 上昇・normal）が、いずれも「依存辺 ref_version の x.y 不一致→RULE-004 ERROR」を主張しほぼ同内容になっている。condition で正/負対の意図と思われるが、視点（辺側の定義 vs 版上昇トリガ）の差が本文で明確でなく重複が近接している。
**推奨**: 両 SPEC の責務境界（9-1=ドリフト定義の failure、10=版上昇トリガの normal）を本文で明示するか、統合を検討する。オーナー判断。
**対応状況**: resolved（責務境界を明記し統合しない判断を反映・2026-07-11）
**指摘時 ref_version**: SPEC-10 "0.2"（ノードバッジ x.y 基準・DD-8）
