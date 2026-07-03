**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→SPEC-31 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 SPEC-31（empty を使用する in-graph アンカー）から `→FND-13` の backward 辺を受けており、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録（DD-3）。

**内容**: condition 語彙が normal/boundary/failure/error の4語のみで、空集合・ゼロ件・null・未設定（in-graph 0 件など）を表す独立クラスが無かった。これらを normal や boundary に混ぜると等価分割が崩れ、テスト設計上の網羅穴になる。SPEC-31（in-graph 0 件）を著作する際にこの語彙不足が顕在化した。
**対応状況**: resolved
**対応内容**: `config.yaml` の condition_vocab に `empty` を追加し5語化（normal/boundary/empty/failure/error）、各語の説明コメントを追記。語彙を列挙する全箇所（spec.md 冒頭ガイド・04-notation・07-authoring-guide・02-meta-schema DD-010・01-document-items・spec-author/test-strategy/io-event-ledger）を5語へ更新。SPEC-31 が empty を使用。SPEC-31 に `→FND-13` バックリファレンス辺を付与済み（reconciliation が付与）。なお発生源の `config.yaml` は out-of-graph（trace_scope.exclude）のためノードを持たず、in-graph アンカーとして SPEC-31 に紐づけた。
**指摘時 ref_version**: SPEC-31 "0.1"（doc-system/02-what/03-spec.md・SPEC-31 バッジ v0.1 時点・in-graph アンカー）
