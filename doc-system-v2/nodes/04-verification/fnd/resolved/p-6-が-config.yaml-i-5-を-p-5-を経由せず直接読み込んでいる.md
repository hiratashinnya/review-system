**深刻度**: ERROR

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→P-6 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 P-6 から `→FND-21` の backward 辺を受けており、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録（DD-3）。

**内容**: P-6（in-graph 集合決定）の edges に `to: I-5`（config.yaml）があり、DFD Level 1 でも `FS → I-5 → P-6` と config を直接読み込んでいる。設定の読み込み・検証は P-5（設定ファイル読み込み）の単一責務であり、P-6 が config を二重に読むと (a) 設定の解釈が 2 箇所に分散し、(b) 検証済み設定オブジェクトという単一の真実源を経由しない。P-6 は P-5 が生成する検証済み設定オブジェクト（trace_scope を含む）を受け取るべきで、ファイル（I-5）を直接読むべきでない。
**対応状況**: resolved
**対応内容**: 検証済み設定オブジェクトを内部データ D-3 として起票（io.md・D-2 は FND-8 で退役済みのため D-3 を採番）。P-5 を D-3 の生成元（D-3→P-5）、P-6 を消費先（P-6→D-3）に再配線し、P-6 の `to: I-5` 辺を削除した。P-6 に `→FND-21` バックリファレンス辺を付与。
**指摘時 ref_version**: P-6 "0.6"（processes.md v0.6.5 時点・forward 辺の指摘時版＝ref "0.1"）
