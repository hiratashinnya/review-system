**深刻度**: ERROR

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→SPEC-14-1 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 SPEC-14-1 から `→FND-24` の backward 辺を受ける（backref 付与）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: SPEC-14-1（カバレッジテーブルの出力フォーマット・normal）の edges が `to: SPEC-14`（親 SPEC）と `to: FND-18` のみであり、FR または NFR への直接辺が存在しない。config.yaml の `must_link_to: SPEC → [FR, NFR]`（RULE-006・severity: error）違反。SPEC-14-1 は SPEC-14 の -N 分割ノードだが、config の必須接続は FR/NFR への直辺を要求しており、SPEC→SPEC のみでは RULE-006 を満たさない。
**推奨**: config の `must_link_to` の OR リストを `SPEC → [FR, NFR, SPEC]` に拡張し、子 SPEC（`-N` 採番）を機構として持つ。あるいは SPEC-14-1 に `to: FR-6` 直辺を付与する。**前者を推奨**（子 SPEC を今後も使うなら機構として持つべきで、SPEC-48 本文・接続マトリクスの意図と一致する）。本 PR が初めて子 SPEC（`-N` 採番）パターンを導入したが、config 側に `SPEC → SPEC` が用意されていなかった点が根因。
**対応状況**: resolved
**対応内容**: `docs/doc-system/config.yaml` の `must_link_to: SPEC` を `target: [FR, NFR, SPEC]` に拡張（FND-25 と同根一括解消）。SPEC-14-1 に `→FND-24` バックリファレンス辺を付与（spec.md v0.3.6）。接続マトリクス §2 SPEC 行に NFR ✅・SPEC ✅ を追加（connection-matrix.md v0.2.1）。
**指摘時 ref_version**: SPEC-14-1 "0.3"（doc-system/02-what/03-spec.md v0.3.5 時点）
