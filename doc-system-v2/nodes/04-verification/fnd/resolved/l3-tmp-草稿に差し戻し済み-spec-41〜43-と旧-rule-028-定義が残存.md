**深刻度**: INFO

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→FND-18 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。FND-18 は provenance（FND→FND・本文記録のみ・backref なし）。既存 incoming（VERIFY-1）で非孤立。指摘時 ref_version は本文に記録（DD-3）。

**内容**: `tmp/doc-system/spec-41-49.md` に FND-18 初回処置で差し戻し済みの SPEC-41（I-1 完全スキーマ）・SPEC-42（O-2 カバレッジ出力）・SPEC-43（I-7 テンプレート構造）の草稿が残存し、最終 spec.md（v0.3.5）の RULE-028 定義とは異なるバージョンの RULE-028 記述が含まれる。`tmp/doc-system/fnd18-redo.md` にも旧 RULE-028 定義が含まれる。tmp は working draft であり主ファイルとは独立するが、同一 SPEC ID の別定義が検索時に混乱を生む恐れがある。また tmp/doc-system/n5-verify-fnd.md にも RULE-028 への参照がある。
**補足**: `tmp/doc-system/spec-41-49.md` の SPEC-41 は RULE-028 を「unknown field → WARNING」と定義しているが、最終 spec.md の RULE-028 は `labels`/`scheduled`/`edges` の欠如・型不正 → ERROR で**別物**であり、将来の誤参照源になる。tmp 草稿9本が最終版と重複してコミットされている。
**推奨**: tmp をコミットしない運用にする（`.gitignore` 追加など）か、撤去分（差し戻し済み SPEC-41/42/43 を含む草稿）を削除する。
**対応状況**: resolved
**対応内容**: 旧 RULE-028 定義を含む草稿 `tmp/doc-system/spec-41-49.md`（差し戻し済み SPEC-41〜43 を含む）と `tmp/doc-system/fnd18-redo.md` を削除。バックリファレンス辺の付与先は tmp ファイル（in-graph ノードなし）のため付与先なし。
**指摘時 ref_version**: FND-18 "0.1"（doc-system/04-verification/02-findings.md v0.1.10 時点）
