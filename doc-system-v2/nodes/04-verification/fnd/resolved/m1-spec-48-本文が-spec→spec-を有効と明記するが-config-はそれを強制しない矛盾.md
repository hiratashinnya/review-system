**深刻度**: WARNING

**改訂理由（z バンプ v0.1.0→v0.1.1・FND-111 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠・DD-21 確定）**:
FND-111（resolved-flag ドリフト 19 件一括是正）に伴い辺逆転を完了。元 forward 辺（`→SPEC-48 "0.1"`）を削除し `edges: []`・`resolved: true` を付与。処置対象 SPEC-48 から `→FND-25` の backward 辺を受ける（backref 付与）。指摘時 ref_version は本文に記録（DD-3）。

**内容**: SPEC-48（各ノードは直接の親のみへ辺を張る・USDM 1段制約）の本文に「接続マトリクスで SPEC の直接親は FR または別 SPEC と定義されている」「SPEC の `edges[].to` が FR・NFR・または別 SPEC（直接親 SPEC）を指す」と明記されている。一方 config.yaml の `must_link_to: SPEC → [FR, NFR]` には SPEC→SPEC は含まれておらず、機械検査上は SPEC→SPEC のみのノードが RULE-006 ERROR になる。FND-24（SPEC-14-1）の違反はこの不整合が根因。SPEC-48 本文か config の `must_link_to` のいずれかを修正する必要がある。
**推奨**: FND-24 と同根のため一括解消する。config を `SPEC → [FR, NFR, SPEC]` に拡張すれば、SPEC-48 本文（「SPEC の辺は FR・NFR・または別 SPEC を指す」）と config の機械判定が一致する。config を拡張せず SPEC-48 本文側を狭める選択肢もあるが、子 SPEC パターンを採用する方針なら config 拡張を推奨。
**対応状況**: resolved
**対応内容**: FND-24 と同根一括解消。`docs/doc-system/config.yaml` を `SPEC → [FR, NFR, SPEC]` に拡張することで SPEC-48 本文の記述と config の機械判定が一致した。SPEC-48 に `→FND-25` バックリファレンス辺を付与（spec.md v0.3.6）。
**指摘時 ref_version**: SPEC-48 "0.3"（doc-system/02-what/03-spec.md v0.3.5 時点）
