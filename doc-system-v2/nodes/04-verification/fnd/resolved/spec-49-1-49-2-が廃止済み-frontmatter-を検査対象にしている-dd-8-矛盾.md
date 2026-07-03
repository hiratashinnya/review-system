**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→SPEC-49 "0.1"`・`→DD-8 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 SPEC-49 から `→FND-85` の backward 辺を受ける（backref 付与）。DD-8 は provenance（本文記録のみ・backref なし）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: アンブレラ SPEC-49 の概要は「状態は本文見出しバッジにのみ記載される」と正しく述べているが、子 SPEC-49-1/49-2 の前提条件・入力/トリガ・期待動作は「frontmatter に `status:`/`lifecycle:`/`state:` キーが存在するか」を検査対象としている。DD-8（2026-06-14 確定・反映済）でファイルレベル YAML フロントマターは全廃され、ノードデータはインライン YAML ブロック（`<details>` 内）にのみ存在する。したがって「frontmatter」は実在しない検査対象であり、DD-8 および NFR-1（プレーンテキスト・フロントマター廃止）と齟齬する。検査対象が存在しないため、本来検出すべき「ノード YAML ブロックへの status 系キー混入」を取りこぼす恐れがある（PR4: 観測できないものを持たない、にも抵触）。
**推奨**: SPEC-49-1/49-2 本文の「frontmatter」を「ノード YAML ブロック内のフィールド（`<details>` 内インライン YAML）」へ用語訂正する。SPEC-49 概要の表現と整合させる。DD 昇格が望ましい。
**対応状況**: resolved（2026-06-15）
**処置**: SPEC-49/49-1/49-2 の「frontmatter」表記を「ノード YAML（メタ属性）」へ用語訂正（DD-8 準拠）。NFR-6 は既に「メタ属性」表記のため変更不要。spec-author が SPEC-49 に `→FND-85` バックリファレンス辺を付与済み。
**指摘時 ref_version**: SPEC-49 "0.1"／DD-8 "0.1"（いずれもノードバッジ x.y 基準・DD-8）
