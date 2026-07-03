**深刻度**: ERROR

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→DD-7 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。DD-7 は provenance（本文記録のみ・backref なし）。既存 incoming で非孤立。指摘時 ref_version は本文に記録（DD-3）。

**内容**: `doc-system/03-analysis/00-dfd.md`（v0.2.2）の本文に「本ファイルは派生図（ノードを持たない）」と記載され out-of-graph を自称するが、config.yaml の `trace_scope.include: ["doc-system/**/*.md"]` に含まれ、`trace_scope.exclude` には未登録。spec-inspector はこのファイルを走査しノードを抽出しようとするが、ファイル内には `<details>` YAML ブロックのノードが存在しないため「in-graph ファイルだがノードゼロ」という矛盾状態になる。修正方針：(A) `trace_scope.exclude` に `"**/00-dfd.md"` を追加して out-of-graph を正式化 か (B) out-of-graph 自称を削除しノードを持たない in-graph ファイルとして運用。
**推奨**: **(A) を推奨**。`trace_scope.exclude` に `**/00-dfd.md`（または `doc-system/**/00-dfd.md`）を追加して out-of-graph を正式化する。dashboard を `**/00-dashboard.md` で除外しているのと同じ機構であり、自称と config の食い違い（観測できない前提）を解消できる。
**対応状況**: resolved
**対応内容**: 推奨案 A を採用。`docs/doc-system/config.yaml` の `trace_scope.exclude` に `"**/00-dfd.md"` を追加し、DFD 図ファイルを out-of-graph として正式化した（00-dashboard.md と同等の扱い）。DD-7 に `→FND-27` バックリファレンス辺を付与（decisions.md v0.1.6）。
**指摘時 ref_version**: DD-7 "0.1"（doc-system/04-verification/04-decisions.md v0.1.5 時点）
