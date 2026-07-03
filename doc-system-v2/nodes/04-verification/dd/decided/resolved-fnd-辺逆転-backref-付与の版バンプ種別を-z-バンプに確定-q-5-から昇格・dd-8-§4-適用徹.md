**status: decided**（2026-06-28 オーナー決定・選択肢A 採用／選択肢D 却下）

> **辺の扱い**: 本 DD は decided。被参照は昇格元 Q-5 の `→DD-21`（昇格辺）で確保され RULE-005（完全孤立）は生じない。先例（Q-3→DD-20・Q-4→DD-16・DD-15〜DD-20 はいずれも `edges: []`）に倣い本 DD は `edges: []` とする。**75 FND は resolved（`fnd_lifecycle.resolved.must_not_link_to: any`）のため `→DD-21` の forward 辺を持てない**——よって本決定の provenance は各 FND 本文の改訂理由（「Q-5/DD-21 により z へ訂正」）に記録し、辺は張らない（DD-16 が FND-96 等へ辺を張らず provenance を本文記録した先例と同型）。5 件の backref 保持ノード（D-18/P-7-2/FR-5/FR-1/DM-1）も本文で DD-21 を参照し、辺の追加は行わない（churn 最小化）。
> **指摘時 ref_version の記録（DD-3 制度）**: 本 DD は Q-5 から昇格（DD であり FND でない）ため不要（DD-16〜20 と同扱い）。論点・現状の出所は Q-5（05-questions.md・指摘時 FND-101 "0.2"／SPEC-9 "0.2"／DD-8 "0.1"）。

**論点**（Q-5 より昇格・要約）: resolved FND の辺逆転（forward 辺 `FND→対象` の削除＋`resolved: true` 化）と、処置対象側への backref 辺 `対象→FND` 付与に伴う版バンプを、**MINOR とすべきか z（PATCH）とすべきか**。A-1（FND-101 辺逆転一括是正）で 75 FND を MINOR バンプした結果、それらを指す backref/affects 辺（ref_version 据え置き）が一斉ドリフトし、新規 101 件の RULE-004 ドリフトが発生した。この是正方針を確定する。

**現状**（Q-5 で点検確認済みの定量事実）:
- A-1 実施後にグラフ全体のドリフトを点検したところ、**A-1 が 101 件の新規 backref ドリフト（X→FND）を生んだ**（A-1 前 main=103 件 → A-1 後=182 件・新規分のうち 101 がこの種）。
- 原因：A-1 で 75 件の resolved FND を **MINOR バンプ**（例 v0.1.0→v0.2.0）し、それらを指す backref 辺（処置対象 X→FND-x・provenance）の ref_version が "0.1" のまま残り、FND バッジの x.y 変化によって `_drift()`（SPEC-9 v0.2.1＝RULE-004）が一斉ドリフトと判定した。
- 補強事実：reconciliation は A-1 で新規追加した 5 件の backref を「MINOR だと依存元ドリフトが発生する」として **z バンプに自己訂正**しており（DD-8 §4「backref 辺追加→z バンプ」）、同じ理屈が FND ノード本体の lifecycle 辺逆転にも当てはまる。

**選択肢**（Q-5 より要約）:
- **選択肢A（resolved-FND の辺逆転/backref を z バンプとする・DD-8 §4 適用徹底／採用）**: 75 FND を vX.(Y+1).0 → vX.Y.(Z+1) に再バンプ（x.y を A-1 前＝main の値に戻し z を +1）。x.y 不変で 101 件の新規ドリフトが消える。辺逆転（forward 削除＋`resolved: true`）と backref 付与は **downstream 無影響の provenance/lifecycle 操作**であり、既存 DD-8 §4「backref 辺追加＝z バンプ」と同類。**ルール（SPEC-9・DD-8）の改変は不要で、既存ルールの適用を直すだけ**。
- **選択肢B（MINOR 維持＋全 backref の ref_version を新 badge x.y へ同期）**: 101 件の backref ref を更新。実体のない更新で ref_version の意味を壊す。非推奨。
- **選択肢C（MINOR 維持＋ドリフトを許容ノイズとする）**: FND-101 が目的とした「警告慣れ」問題を悪化させる。非推奨。
- **選択肢D（SPEC-9/RULE-004 で backref/provenance 辺をドリフト判定対象外にするルール改変）**: 版バンプ論争を無意味化するが SPEC-9 改訂＋`_drift()` 実装変更＋テスト追加でスコープ大。**却下**。

**決定**: **選択肢A を採用**（オーナー決定・2026-06-28）。
- resolved FND の辺逆転（forward 削除＋`resolved: true`）と backref 付与は **z（PATCH）バンプ**とする。A-1 で MINOR バンプしたのは誤りであり、75 FND を z バンプへ再訂正する（x.y を A-1 前＝main の値に戻し z を +1）。
- **drift ルール（SPEC-9＝RULE-004）も DD-8 も変更しない**。両者は既に正しく、既存 DD-8 §4「backref 辺追加＝z バンプ」の適用を徹底するのみ（適用を誤っただけで、適用を直す）。
- **選択肢D（backref/provenance 辺をドリフト対象外にするルール改変）は却下**。

**根拠**:
- 辺逆転・backref 付与は参照先の意味内容（FND の指摘事実）を変えず、downstream の再レビューを要さない provenance/lifecycle 操作である。DD-8 §4 は既にこの種を「z バンプ」と定めており、resolved-FND の辺逆転も同類と解するのが整合的（PR2 機械判定の対象を正しく適用する）。
- z バンプなら x.y が不変のため、backref/affects 辺の ref_version（指摘時の版）を据え置いたままドリフトが発生しない。A-1 起因の新規 101 件ドリフトが解消し、FND-101 が目的とした「警告ノイズ低減」を真に達成する。
- reconciliation が 5 件の新規 backref を z バンプに自己訂正した先例（DD-8 §4 適用）と同一の理屈で、FND 本体にも一貫適用する。
- D は原理的により根本的だが SPEC-9 改訂＋コード改修でスコープが大きく実装フェーズ寄り。既存ルールの適用是正（A）で新規ノイズは止まるため、ルール改変は不要と判断し却下。B は ref_version の意味を壊し、C は警告慣れを悪化させるため非推奨。

**接続規則変更チェック（FND-99 パターン）**: 本 DD は **版バンプ種別の運用適用を是正するのみ**で、`config.yaml` の接続規則・`fnd_lifecycle`・`decision_spine`・SPEC-9（RULE-004）のいずれも追加・変更・削除しない（選択肢D 却下のためルール本体は不変）。よって接続マトリクス・ドキュメント一覧・各 author エージェント／スキルへの規則伝播は不要（DD-17/18/19/20 の同チェックと同じ判定）。版バンプ種別は DD-8 で既に定義済みのため DD-8 本体への規則追記も不要。

**影響範囲（A 採用・本ブランチで実施済み）**:
- **75 FND の再バンプ（MINOR → z）**: `doc-system/04-verification/02-findings.md` のバッジと本文版表記を z バンプへ訂正。既存 v0.1.0 群（FND-1〜5,7〜16,19〜23,29,30,32,34,37,38,39,40〜77,80,87,90,95,101）= v0.2.0→**v0.1.1**／FND-6,103,104,105 = v0.3.0→**v0.2.1**／FND-107 = v0.2.0→**v0.1.2**。改訂理由の版種別を「MINOR」→「z」へ訂正済み。
- **5 件の backref ref_version 訂正**: D-18→FND-6 "0.3"→**"0.2"**／P-7-2→FND-29 "0.2"→**"0.1"**／FR-5→FND-80 "0.2"→**"0.1"**／FR-1→FND-107 "0.2"→**"0.1"**／DM-1→FND-107 "0.2"→**"0.1"**。backref 保持ノード自身の z バンプは正しいので維持（ref 値のみ訂正）。
- **Q-5 を昇格・closed 化**: `→DD-21`（ref "0.1"）付与・MINOR バンプ v0.1.0→v0.2.0。
- out-of-graph（不変）: SPEC-9（RULE-004）・DD-8・`config.yaml`・`docidx/query.py` `_drift()`（選択肢D 却下）。

**残課題（別件・要オーナー判断）**: FND-96/97/98/99/100 も A-1 以前に lifecycle 辺逆転で **MINOR バンプ済み**（FND-101 が「是正済み手本」とした scope 外ノード）で、同じ原則違反（main 既存ドリフトの一部＝MOD-1→FND-96 ref0.3/badge0.5 等）。本 DD の原則は等しく当てはまるが、pre-existing かつ改訂履歴が混在（FND-96 は v0.1→v0.4 が正当な MINOR・最終 v0.4→v0.5 のみ lifecycle）するため、本ブランチでは是正せず別途オーナー判断（FND 起票）とする。

**→ 残課題完了（2026-06-28・issue #40）**: FND-96〜100（A-1 漏れコホート）は **FND-110 を起票し本ブランチ（`claude/issue-40-plan-0t1eqc`）で z バンプ適用是正・完了**（FND-96=v0.4.1／FND-97・98・99・100=v0.1.1。MOD-1→FND-96 ref 訂正・MOD-1 に FND-110 被参照アンカー付与）。DD-21 自体は decided 済み・本追記のため z バンプ（v0.1.0→v0.1.1）。

**覆る場合の影響範囲**: 選択肢D（ルール改変）へ移行する場合、SPEC-9（RULE-004）を「backref/provenance 辺をドリフト判定対象外」に改訂し `docidx/query.py` `_drift()` 実装変更＋テスト追加、01-doc-verify.md・関連スキル/エージェントへドリフト意味論変更を周知する（実装フェーズ寄りの別 DD として起票）。本 DD（z バンプ適用）はその場合も無害で、D 移行は上位互換的に追加可能。
