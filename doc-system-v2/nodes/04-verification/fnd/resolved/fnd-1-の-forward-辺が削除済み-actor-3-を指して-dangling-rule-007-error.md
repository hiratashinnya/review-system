**深刻度**: ERROR

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→FND-1 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。`→FND-1` は本 FND の指摘対象＝処置先 FND-1 への provenance 辺（FND→FND）であり、provenance は backref を張らず本文記録のみとする（worklist A-1 指定：FND-1↔FND-16 相互 provenance は双方削除）。本 FND は VERIFY ノード（01-doc-verify.md）からの incoming 辺を保持しており孤立しない（resolved の backward 必須は当該 incoming で充足）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: FND-1（ACTOR-3 系境界誤りの指摘・resolved）が依存辺 `to: ACTOR-3` を保持しているが、ACTOR-3 は FND-1 の処置で削除済みであり、存在しない ID を参照している（RULE-007・always_error＝stage/suppress に関わらず発火）。FND は対象要素への辺が1本以上必須（RULE-006: FND→any）だが、唯一の対象が消滅したため forward 辺が宙に浮いている。FND-1 本文には「削除済みのため付与先なし」と記載済みだが、forward 辺自体は残置されダングリングになっている。
**対応状況**: resolved
**対応内容**: FND-1 の forward 辺を `to: ACTOR-3` から `to: P-1（processes.md v0.6）` に張替え。P-1（ノード受付・パース）は ACTOR-3 の系内処理の役割を担う代表ノード。P-1 に `→FND-1` バックリファレンスを付与済み。FND-1 に `→FND-16` バックリファレンスを付与していたが、DD-16 辺逆転（2026-06-25）で FND-1 の edges を `[]` 化したため当該辺は削除し、本 FND と FND-1 の関係は本文 provenance に維持する（FND-16 自体は VERIFY からの incoming で非孤立）。
**指摘時 ref_version**: FND-1 "0.1"（doc-system/04-verification/02-findings.md・FND-1 バッジ v0.1 時点・dangling 修正の処置先＝provenance）
