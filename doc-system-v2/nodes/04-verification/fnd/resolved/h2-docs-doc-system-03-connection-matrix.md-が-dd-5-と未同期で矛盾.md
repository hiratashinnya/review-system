**深刻度**: ERROR

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→DD-5 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。DD-5 は provenance（本文記録のみ・backref なし）。既存 incoming（VERIFY-1/DD）で非孤立。指摘時 ref_version は本文に記録（DD-3）。

**内容**: DD-5（NFR から SPEC 導出を必須化・2026-06-13 反映完了）により config.yaml が `must_link_to: SPEC → [FR, NFR]` に更新され `must_be_linked_from: NFR ← [SPEC]` が追加されたが、`docs/doc-system/03-connection-matrix.md`（v0.2.0）は更新されていない。具体的な不整合：§2 接続要否マトリクス表の SPEC 行が FR のみ必須（NFR なし）・§4「NFR は `refines` 上流にはならない（他要素が NFR を refines しない）」が DD-5 の「SPEC→NFR を必須化」と直接矛盾。接続マトリクスは「人が読める全体像」として正本 config.yaml と一致すべきだが、DD-5 適用後に同期されていない。
**推奨**: `docs/doc-system/03-connection-matrix.md` を DD-5 に合わせて §2/§3/§4 とも改訂する。具体的には (§2) must_link_to の mermaid を `SPEC --> FR` のみから `[FR, NFR]` 相当へ拡張・(§3) 被依存表に `NFR ← SPEC` を追加（現状 `NFR ← FND/TC/VERIFY` のみ）・(§4)「NFR は refines 上流にはならない（他要素が NFR を refines しない）」の記述を DD-5（`SPEC → NFR` 必須化）と整合する形に改訂。正本ドキュメント間（config と接続マトリクス）の矛盾を残したまま DD-5 を decided にするのは「矛盾は停止して打ち上げ」原則（PR）違反であり、マージ前解消が望ましい。
**対応状況**: resolved
**対応内容**: `docs/doc-system/03-connection-matrix.md` を v0.2.1 に改訂。§1 mermaid に `SPEC --> NFR` と `SPEC --> SPEC` を追加、§2 表に NFR 列を追加（SPEC 行: FR ✅・NFR ✅・SPEC ✅）、§3 被依存表に `NFR ← SPEC`（requirements 以降）行を追加、§4 テキストを DD-5 に合わせて改訂。DD-5 に `→FND-26` バックリファレンス辺を付与（decisions.md v0.1.6）。
**指摘時 ref_version**: DD-5 "0.1"（doc-system/04-verification/04-decisions.md v0.1.5 時点）
