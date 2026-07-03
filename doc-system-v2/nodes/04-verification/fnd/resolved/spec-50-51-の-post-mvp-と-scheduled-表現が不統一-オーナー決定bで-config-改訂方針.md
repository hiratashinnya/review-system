**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→SPEC-50 "0.1"`・`→SPEC-51 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 SPEC-50 から `→FND-78`・SPEC-51 から `→FND-78` の backward 辺を受ける（backref 付与）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: SPEC-50/51 は `labels:[post-mvp]` だが `scheduled:""`（空）である。一方 SPEC-28/40 は `scheduled:"post-mvp"` と表現しており、post-mvp の表現が不統一。scheduled は SPEC-20（後フェーズ完全サイレント判定）に影響する属性のため放置不可で、同じ post-mvp 扱いの SPEC 群でラベルと scheduled の使い分けが揺れている。
**推奨**: オーナー決定B（2026-06-14）＝`config.yaml` の `phases` から `post-mvp` を除去し、`scheduled` は実スプリント（sprint-*）のみ許可する。SPEC-28/40/50/51 の `scheduled` を実スプリント（例 sprint-2）へ設定し、`scheduled ∈ phases` を強制する RULE を新設して空 scheduled と非 phases 値を違反化する。config・RULE 一覧・接続マトリクスの改訂を伴うため DD 昇格が望ましい。
**対応状況**: resolved（DD-9 / 2026-06-14）
**指摘時 ref_version**: SPEC-50 "0.1"／SPEC-51 "0.1"（いずれもノードバッジ x.y 基準・DD-8）
