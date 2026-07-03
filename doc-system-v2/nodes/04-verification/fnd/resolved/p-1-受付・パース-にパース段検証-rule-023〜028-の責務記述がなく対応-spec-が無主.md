**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い辺逆転を完了。元 forward 辺（`→P-1 "0.2"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 P-1 から `→FND-20` の backward 辺を受けており、新 fnd_lifecycle の resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録（DD-3）。

**内容**: P-1「受付・パース」は構造化ノードセットを生成するが、本文の責務記述にパース段検証（RULE-023〜028）が含まれていない。対応する SPEC-2（RULE-023）・SPEC-32（RULE-024）・SPEC-33（RULE-025）・SPEC-34（RULE-026）・SPEC-35（RULE-027）・SPEC-36（テンプレ由来 RULE-025/026）・SPEC-52（スキーマ適合）・SPEC-53（RULE-028）が、どの P からも参照されない無主状態であり、FR/SPEC の裏付けを持つ機能が分析層のプロセスに接続されていない＝価値経路の穴（PR6）。P-1 はパース処理そのものを担うため、これらパース段検証は P-1 の単一責務（パース段処理）に含めるのが妥当である。
**対応状況**: resolved
**対応内容**: P-1 の責務記述を「パース＋パース段検証（RULE-023〜028）」に明確化し、SPEC-2/32/33/34/35/36/52/53 への依存辺を P-1 に追加した（P-2-2 が複数 RULE を1責務で持つのと同様、パース段処理は単一責務として保持し分解しない）。SPEC-36（テンプレ由来の必須欠如）はその期待動作が RULE-025/026 の検出報告であり、検出主体は P-1（パース段）であるため P-1 に接続（VERIFY-3 後の spec-inspector 点検 G1 を反映）。P-1 に `→FND-20` バックリファレンス辺を付与済み（processes.md v0.6.3→0.6.4）。なお SPEC-31（empty・in-graph 0 件）はパースではなく in-graph 集合決定/オーケストレーションの責務のため P-1 には含めず、別途 P-6/orchestration の論点として残す。
**指摘時 ref_version**: P-1 "0.6"（processes.md v0.6.3 時点・forward 辺の指摘時版＝ref "0.2"）
