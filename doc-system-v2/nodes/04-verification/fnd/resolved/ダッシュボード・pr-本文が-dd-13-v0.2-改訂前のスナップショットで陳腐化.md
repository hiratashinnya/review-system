**改訂理由（z バンプ v0.1→v0.1.1・FND-110/DD-21 適用是正）**:
Q-4 選択肢A 採用（DD-16）により `fnd_lifecycle` 専用ルールが正式定義されたため、暫定措置の `suppress: [RULE-006]` を撤去し `resolved: true` で機械判定可能にする。本 FND は処置対象 DD-13（v0.3）から `→FND-98`（backward 辺）を受けており、新 `fnd_lifecycle` の resolved ルール（backward 必須・forward 不在期待・`edges: []`）を満たす。指摘内容・深刻度・対応状況（resolved）は不変（suppress 撤去＋`resolved` フィールド追加＝lifecycle 操作のため MINOR バンプとして記録していたが、DD-21 の確定原則「resolved-FND の辺逆転/backref 付与は z バンプ」に照らし FND-110 で是正、z バンプへ訂正）。

**深刻度**: WARNING

**内容**: ダッシュボード（doc-system/00-dashboard.md）と PR #28 本文が、DD-13 v0.2 改訂（MOD 粒度を C 案へ・MOD-1〜18 へ拡張）・DD-15 追加・ORC-2 新設を反映しておらず、旧スナップショット（DD-13 v0.1・MOD-1〜12・ORC-1 のみ）のまま陳腐化している。DD-13 の決定内容がダッシュボード上で誤って表現されている（ダッシュボードは trace_scope.exclude で out-of-graph のため、誤表現の原因ノードである DD-13 を edges.to 先とする）。PR #27 ② と同種のドキュメント陳腐化の再発。

陳腐化していた箇所（4 箇所）:
1. ダッシュボード DD-13 サマリ行（🧭 DD / Q / PEND サマリ）: 「MOD 粒度：L1 親プロセス単位（B 案）＋P-2-5 例外。MOD-1〜12 で採用（2026-06-16）」のまま。
2. ダッシュボード直近作業 N2 行（🔄 直近の作業）: 「MOD-1〜12 / … / ORC-1 著作・反映。DD-13/DD-14 起票」のまま。
3. ダッシュボード完了済み行（🔥 推奨ネクストアクション > 完了済み）: 「N2（… MOD-1〜12/…/ORC-1 著作・DD-13/DD-14 … 2026-06-16）」のまま。
4. PR #28 本文: タイトル・本文が「MOD-1〜12 … ORC-1 … DD-13/DD-14」のままで MOD-13〜18 / ORC-2 / DD-15 / DD-13 v0.2 が未記載。

**対応状況**: resolved

**対応内容**: 解消と同時起票。ダッシュボード 3 箇所（DD-13 サマリ行・直近作業 N2 行・完了済み行）を DD-13 v0.2（C 案・MOD-1〜18・2026-06-20）・DD-15・ORC-2 を反映した記述へ更新済み。PR #28 本文は GitHub 側で更新済み。指摘の原因ノード DD-13 に `→FND-98` のバックリファレンス辺を付与する（reconciliation 反映時）。

**指摘時 ref_version**: DD-13 "0.2"（doc-system/04-verification/04-decisions.md の DD-13 ノードバッジ v0.2 時点・陳腐化の原因ノード＝辺逆転で削除した元 forward 辺 `→DD-13` の処置対象。現在は DD-13 v0.3 から `→FND-98` backref を受ける）
