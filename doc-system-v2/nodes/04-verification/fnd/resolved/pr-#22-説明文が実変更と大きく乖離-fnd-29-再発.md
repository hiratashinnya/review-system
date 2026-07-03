**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→FND-29 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。`→FND-29` は同型の先行指摘 FND-29（PR 説明文乖離）への provenance 辺（FND→FND）であり、provenance は backref を張らず本文記録のみとする。本 FND の実処置対象は PR #22 description（out-of-graph・GitHub 成果物）であり、唯一の辺であった `→FND-29` を削除すると incoming/outgoing をともに持たず**完全孤立**する（本 FND への唯一の incoming であった FND-29→FND-38 も、FND-29 の辺逆転で削除されるため）。

> **🔴 孤立エラーの意図的保持（FND-99 先例に倣う・恣意的抑制の禁止）**: 上記の結果、FND-38 は RULE-005（完全孤立・always_error・抑制不可）のエラーを発火する。これは欠陥ではなく、**「FND-38 は resolved だが、その処置（PR #22 description の更新）を引き受けるバックリファレンス対象が in-graph ノードとして存在しない」状態を正しく示す意図的なシグナル**である。`→FND-29` を backref に転用しないのは、FND-29 が本 FND-38 の**処置対象ではなく provenance（同型の先行指摘）**であり、provenance（FND→FND）に backref を張らない原則（worklist A-1・FND-99 先例）に従うため。`suppress` は付けず、エラー発火状態を意図的に保持する。実処置対象は PR #22 description（out-of-graph）のため backward 辺の**付与先なし**であり、これは resolved-FND の意図的孤立（in-graph 処置対象が存在しない）を正しく示すシグナルである。

**内容**: PR #22 のタイトル「fix: H1/H2/H3 処置（FND-24〜27 resolved）」および本文は、H1/H2/H3 処置のみを記述しており、以下の大規模変更が一切記載されていない：DD-8 確定（ノードバージョニング全面移行）・ファイルフロントマター全廃（30ファイル超）・ref_version 意味論変更（ファイル x.y → ノードバッジ x.y）・live 辺 170 件再基準化・RULE-004/meta-schema/notation/config 再定義・FND-34〜37 起票および一部 resolved・`.gitignore` 追加による tmp 非コミット化（−2400 行超）。PR #21 レビューで起票した FND-29（PR 説明文乖離）の再発であり、レビュアーが実際の変更範囲（プロジェクトのバージョニング哲学の構造的変更）を正しく評価できない状態になっている。
**推奨**: PR 分割はしない（オーナー方針）。PR タイトルと本文を実態に合わせて更新する（タイトル例：`feat: H1/H2/H3 処置 + DD-8 ノードバージョニング全面移行`・本文に全変更の概要を追記）。
**対応状況**: resolved
**対応内容**: PR タイトルを `feat: H1/H2/H3 処置 + DD-8 ノードバージョニング全面移行（FND-24〜37 反映）` に更新し、本文に全変更区分（DD-8 移行・フロントマター全廃・ref_version 再基準化・FND-34〜37・tmp 非コミット化）の概要を追記した。
**指摘時 ref_version**: FND-29 "0.1"（doc-system/04-verification/02-findings.md v0.1.8 時点・同型の先行指摘＝provenance）
