**深刻度**: INFO

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→SPEC-44 "0.2"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 SPEC-44 から `→FND-86` の backward 辺を受ける（backref 付与）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: 横断: SPEC-44〜49（SPEC-44 を代表アンカーとして指摘）。SPEC-44〜49 の出力例は検証ルール ID として `{NFR-id}-check`（例 `NFR-1-check`・`NFR-4-check`）を使用するが、正準ルール台帳は `RULE-NNN`（`docs/doc-system/05-verification.md`）である。NFR 由来の本文検査が正式に RULE 番号を持つのか、`{NFR-id}-check` が暫定識別子なのか、出力契約上の識別子規約が定義されていない。出力契約（O-1 RULE 違反レポート）における違反 ID の名前空間が二重化しており、消費側（reconciliation・spec-inspector）の解釈がぶれる。
**推奨**: NFR 由来検査の出力ルール ID 規約を確定する（RULE-NNN への正式採番 or `{NFR-id}-check` の正式採用）。確定後は台帳（`05-verification.md`）に記載し、SPEC-44〜49 の出力例を統一する。
**対応状況**: resolved（DD-11 / 2026-06-15）
**処置**: DD-11 で `{NFR-id}-check` を NFR 由来本文検査の正式 rule-id 体系として採用（選択肢 B）。`docs/doc-system/05-verification.md` の RULE 台帳に1家族として登録する（reconciliation 反映後に主文脈で実施）。SPEC-44〜49 の出力例は据置。バックリファレンスは DD-11 が `→FND-86` 辺を保持（FND→DD の通常逆転ではなく、DD が解消起点のため DD 側に辺を持つ）。
**指摘時 ref_version**: SPEC-44 "0.2"（ノードバッジ x.y 基準・DD-8）
