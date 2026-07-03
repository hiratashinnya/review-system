**深刻度**: INFO

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→FR-1 "0.3"`・`→FND-36 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 FR-1 から `→FND-32` の backward 辺を受けており、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。`→FND-36` は本 FND-32 の処置を是正した後続 FND-36 への provenance 辺（FND→FND）であり、provenance は backref を張らず本文記録のみとする。指摘時 ref_version は本文に記録（DD-3）。

**内容**: `doc-system/02-what/01-fr.md` 内の FR-1 ノードのバッジが `⬡ FR-1 · v0.3` だが、ファイルの frontmatter は `version: "0.2.5"`（x.y=0.2）。バッジの v0.3 はノード自体の改訂回数カウント、ファイル x.y はファイル全体の MAJOR.MINOR という別体系だが、ノードバッジと ref_version（ファイル x.y 基準）の対応関係が記法ガイドに明示されておらず、読者がバッジの意味を誤解する恐れがある。バッジが「ファイルの x.y」を示すと誤解した場合、ref_version: "0.2.0" との乖離（v0.3 vs 0.2）が誤りに見える。なお ref_version は `"0.2"` で RULE-004 上は正であり、誤読防止のためバッジ採番ルール（ノード改訂回数 vs ファイル x.y）の記法ガイド明記が望ましい。
**対応状況**: resolved
**対応内容**: `docs/doc-system/04-notation.md` の summary バッジ説明箇所に「バッジは著作・最終更新時のファイル x.y スナップショットであり、ノード改訂カウントではない。現在のファイル x.y と一致しなくても RULE 違反にはならない」旨を追記。FR-1 に `→FND-32` バックリファレンス辺を付与（fr.md v0.2.6）。※本 FND-32 の処置（「ファイル x.y スナップショット」定義）は実態と乖離していたことが FND-36 で指摘され、DD-8 により「ノード固有バージョン（MAJOR.MINOR）」定義に是正済み（2026-06-14）。
**指摘時 ref_version**: FR-1 "0.2"（doc-system/02-what/01-fr.md v0.2.5 時点・処置対象）／FND-36 "0.1"（02-findings.md・本処置を是正した後続指摘＝provenance）
