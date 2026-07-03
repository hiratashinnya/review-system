**深刻度**: INFO

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→FND-33 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。`→FND-33` は本指摘の根拠となった先行 FND-33（tmp 非コミット推奨）への provenance 辺（FND→FND）であり、provenance は backref を張らず本文記録のみとする。本 FND の実処置対象は `.gitignore`（out-of-graph・ノードでない）であり、唯一の辺であった `→FND-33` を削除すると incoming/outgoing をともに持たず**完全孤立**する（FND-33 は VERIFY からの incoming を別途保持するため FND-33 自体は孤立しない）。

> **🔴 孤立エラーの意図的保持（FND-99 先例に倣う・恣意的抑制の禁止）**: 上記の結果、FND-37 は RULE-005（完全孤立・always_error・抑制不可）のエラーを発火する。これは欠陥ではなく、**「FND-37 は resolved だが、その処置（.gitignore への `tmp/` 追加）を引き受けるバックリファレンス対象が in-graph ノードとして存在しない」状態を正しく示す意図的なシグナル**である。`→FND-33` を backref に転用しないのは、FND-33 が本 FND-37 の**処置対象ではなく provenance（先行指摘）**であり、provenance（FND→FND）に backref を張らない原則（worklist A-1・FND-99 先例）に従うため。`suppress` は付けず、エラー発火状態を意図的に保持する。実処置対象は `.gitignore`（out-of-graph）のため backward 辺の**付与先なし**であり、これは resolved-FND の意図的孤立（in-graph 処置対象が存在しない）を正しく示すシグナルである。

**内容**: FND-33 で「tmp をコミットしない運用（`.gitignore` 追加など）」を推奨し旧草稿を削除したが、本 PR #22 で新たに `tmp/doc-system/verify5.md` がコミットされた（Stop フックの untracked 検知による）。FND-33 推奨の tmp 非コミット運用が継続されていない。なお verify5.md の本文は VERIFY-5 として 01-doc-verify.md に反映済みであり tmp 版は冗長。
**推奨**: `.gitignore` に `tmp/` を追加して tmp を非コミット化するか、tmp を「著作エージェント出力の履歴成果物」として意図的に追跡する運用をオーナーと合意する。現状は方針未確定のまま Stop フックに従って都度コミットされており一貫性がない。
**対応状況**: resolved
**対応内容**: オーナー判断（2026-06-14）で「`.gitignore` に `tmp/` を追加して非コミット化」を採用。`.gitignore` に `tmp/` を追記し、追跡済みの tmp 草稿（tmp/doc-system/・tmp/sprint-1/）を `git rm --cached` でインデックスから除去（ローカルには残置）。草稿は reconciliation が本ファイルへ反映するため履歴成果物ではなく、非コミット化が妥当（FND-33 推奨の継続）。
**指摘時 ref_version**: FND-33 "0.1"（doc-system/04-verification/02-findings.md v0.1.14 時点・先行指摘＝provenance）
