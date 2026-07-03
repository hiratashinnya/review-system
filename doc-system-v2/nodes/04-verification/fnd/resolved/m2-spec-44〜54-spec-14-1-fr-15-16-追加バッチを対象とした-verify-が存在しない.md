**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→FR-15 "0.1"`・`→SPEC-54 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 FR-15 から `→FND-28`・SPEC-54 から `→FND-28` の backward 辺を受ける（backref 付与）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: VERIFY-1（2026-06-11）・VERIFY-2（2026-06-12 N0 再点検）・VERIFY-3（2026-06-13 P 単一責務）は、それぞれの対象範囲以降に追加された SPEC-44〜54・SPEC-14-1・FR-15/16 を含まない。これらの追加バッチ（NFR→SPEC 導出強化・依存グラフ機能・SPEC-14-1 など）について spec-inspector による参照整合・カバレッジ・RULE 検査の記録がなく、FND-24（SPEC-14-1 RULE-006 違反）が VERIFY から漏れた事実も VERIFY 空白を示す。追加バッチ全体を対象とした VERIFY を起票する必要がある。
**補足**: dashboard の「ステージ別完成度」は requirements を「✅ N0 再点検済」と表示しているが、06-13 に追加された SPEC-44〜54・SPEC-14-1・FR-15/16 は VERIFY で再走査されておらず、実際 H1（FND-24）のような未検出違反が残っている。「✅点検済」表示が実態を上回っている。
**推奨**: 追加分を対象とした VERIFY を起票する（H1〜H3 解消後にまとめて再走査するのが望ましい）か、requirements 層のステータスを 🟡 に戻す。
**対応状況**: resolved
**対応内容**: H1〜H3 処置（FND-24〜27・2026-06-14）完了後、SPEC-44〜54・SPEC-14-1・FR-15/16 を対象とした VERIFY-5 を起票（01-doc-verify.md v0.1.5）。手動点検で PASS を確認。SPEC-14-1 の RULE-006 違反（FND-24）は H1 処置で解消済みであることを確認した。バックリファレンス辺は VERIFY-5 の edges に `→FND-28` を含む形で付与済み。
**指摘時 ref_version**: FR-15 "0.2"（doc-system/02-what/01-fr.md v0.2.5 時点）、SPEC-54 "0.3"（doc-system/02-what/03-spec.md v0.3.5 時点）
