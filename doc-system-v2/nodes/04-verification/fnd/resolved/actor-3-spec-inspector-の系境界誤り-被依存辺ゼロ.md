**深刻度**: ERROR

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→P-1 "0.2"`・`→FND-16 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 ACTOR-3 は削除済みのため、その系内処理役を吸収した P-1 から `→FND-1` backward 辺を受けており（processes.md）、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。`→FND-16` は FND-16（FND-1 の dangling 修正を指摘した FND）への provenance 辺であり、provenance（FND→FND）は backref を張らず本文記録のみとする（FND-16 は別途 VERIFY からの incoming を保持し孤立しない）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: ACTOR-3（spec-inspector）は外部 ACTOR として置かれているが、spec-inspector は本システム（検証 CLI）そのもの＝**系内処理**であり、既存の P-1〜P-4 と同一実体の二重表現である。out 辺は `→SR-4` のみで、E/I/O いずれからも被依存辺を受けず（`must_be_linked_from: ACTOR ← [E,I,O]` 違反・実質孤立に近い）、価値到達経路から浮いている。系外＝非アクタ（PR3/PR4）の原則に反する。
**対応状況**: resolved
**対応内容**: ACTOR-3 を削除し、spec-inspector を系内処理（P-1〜P-4）へ一本化した（actors.md v0.2→0.3）。ACTOR-3 は削除済みのためバックリファレンス辺の付与先ノードが存在しない。ACTOR-3 の役割を吸収した P-1（ノード受付・パース）を forward 辺の張替え先とした（FND-16 対応）。P-1 に `→FND-1` バックリファレンスを付与済み。
**指摘時 ref_version**: ACTOR-3 "0.2"（actors.md v0.2 時点・当該ノードはその後削除済み）／forward 辺の指摘時版＝P-1 "0.2"（processes.md・張替先）・FND-16 "0.1"（02-findings.md・dangling 修正根拠＝provenance）

> **注（DD-3 履歴保全）**: 元の指摘対象 ACTOR-3 は v0.2 時点で削除済みのため、forward 辺は系内処理 P-1 を指す張替え状態であった。辺逆転（DD-16）でこれを削除し、上記に指摘時の版を凍結記録して provenance を保持する。FND-16 への辺は provenance（FND→FND）であり backref を張らず本文記録のみとする。
