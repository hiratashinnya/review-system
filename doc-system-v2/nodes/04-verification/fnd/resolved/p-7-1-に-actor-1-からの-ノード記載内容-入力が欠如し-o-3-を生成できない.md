**深刻度**: ERROR

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→P-7-1 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 P-7-1 から `→FND-23` の backward 辺を受けており、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録（DD-3）。

**内容**: P-7-1（著作・tmp 出力）の入力は I-7（テンプレート）のみで、仕様著者（ACTOR-1）が著作したい「ノードの記載内容（型・親 ID・辺・本文）」を受け取る入力が台帳に存在しない。テンプレートだけでは中身が決まらず、O-3（著作済みノードファイル）を生成できない＝価値経路の穴（PR6）。著作の本質的入力である記載内容を I ノードとして明示する必要がある。
**対応状況**: resolved
**対応内容**: ACTOR-1 発の入力 I-9（ノード記載内容）を起票（io.md・I-8 は FND-10 で退役済みのため I-9 を採番）。P-7-1 に消費辺 `to: I-9` を付与し、SPEC-54（FR-13 配下・P-7 が I-7＋I-9 を受け取り O-3 を生成）を新設して I-9 と P-7-1 を SPEC-54 に接続した。P-7-1 に `→FND-23` バックリファレンス辺を付与。
**指摘時 ref_version**: P-7-1 "0.6"（processes.md v0.6.5 時点・forward 辺の指摘時版＝ref "0.1"）
