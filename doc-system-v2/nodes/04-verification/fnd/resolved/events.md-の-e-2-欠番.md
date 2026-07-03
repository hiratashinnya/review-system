**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→E-2 "0.3"`・`→DD-4 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 E-2 から `→FND-3` の backward 辺を受けており、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。`→DD-4` は本処置（E-3→E-2 リネーム）の根拠決定 DD-4 への provenance 辺であり、provenance（FND→DD）は backref を張らず本文記録のみとする。指摘時 ref_version は本文に記録（DD-3）。

**内容**: events.md は E-1・E-3 のみで E-2 が欠番。E-1 のスティミュラス「仕様著者または CI」は CI 駆動を含意しており、CI 定期/フック起動が別事象として落ちている疑いがある。削除なら理由、別事象なら起票が必要。
**対応状況**: resolved
**対応内容**: E-3（著作要求）を E-2 へリネームして欠番を補正した（events.md・processes.md P-7 参照追従）。E-2 に `→FND-3` バックリファレンス辺を付与済み。forward 辺は指摘処置対象ノード E-2 を指すよう修正（FND-17 (d) 対応・DD-4 参照）。
**指摘時 ref_version**: E-1 "0.4"（events.md v0.4 時点に欠番として指摘。処置は E-3→E-2 リネームで、現在は E-2 が対象ノード）／forward 辺の指摘時版＝E-2 "0.3"（events.md・リネーム後の処置対象）・DD-4 "0.1"（04-decisions.md・処置根拠＝provenance）
