**status: closed**（2026-06-28 DD-21 へ昇格・オーナー決定＝選択肢A 採用／選択肢D 却下）

**改訂（MINOR バンプ v0.1.0→v0.2.0・昇格辺追加＝構造変更）**: オーナーが選択肢A（resolved-FND の辺逆転/backref は z バンプ・DD-8 §4 適用徹底）を採用し、選択肢D（drift ルール改変）を却下したため、本 Q を DD-21 へ昇格し `status: closed` とする。義務辺 `→DD-21`（ref_version "0.1"・DD-21 現バッジ x.y）を追加。下記「推奨」は起票時のもの（D 本筋/A 暫定）であり、最終決定は DD-21（選択肢A）に従う。指摘時 ref_version は据え置き。

**指摘時 ref_version**: FND-101 "0.1"（02-findings.md の FND-101・本是正の親。起票時は誤 MINOR の v0.2.0 だったが DD-21 で z 訂正され v0.1.1＝x.y "0.1" に確定したため整合）・SPEC-9 "0.2"（01-doc-verify.md の SPEC-9 バッジ v0.2.1 時点・ドリフト＝RULE-004 を定義）・DD-8 "0.1"（04-decisions.md の DD-8 バッジ v0.1.1 時点・版セマンティクスを定義）

> 補足：本論点の機械判定実体は `docidx/query.py` `_drift()`（全辺一律に `ref_version(x.y) != target badge(x.y)` でドリフト判定）だが、これは out-of-graph 資産のため辺を張らず本文参照に留める。

**論点（1文）**: resolved FND の辺逆転（lifecycle 遷移）に伴う版バンプを **MINOR とすべきか z とすべきか**、そもそも **backref/provenance 辺（X→FND・affects 辺等）を RULE-004 ドリフト判定の対象外とすべきか**。

**現状（点検で確認した定量事実）**:
- A-1（FND-101 辺逆転一括是正）実施後にグラフ全体のドリフトを点検したところ、**A-1 が 101 件の新規 backref ドリフト（X→FND）を生んだ**ことが判明した（A-1 前 main=103 件 → A-1 後=182 件・新規 103 のうち 101 がこの種）。
- 原因：A-1 で 75 件の resolved FND を **MINOR バンプ**（例 v0.1.0→v0.2.0）した（forward 辺削除＝構造変更＝DD-8 §4「辺の追加/削除→MINOR」に従った）。それらの FND を指す **backref 辺（処置対象 X→FND-x・provenance）の ref_version は "0.1" のまま**残った。
- `_drift()`（SPEC-9 v0.2.1＝RULE-004）は backref/provenance 辺を除外しないため、FND バッジが x.y 変化した瞬間に全 backref が一斉にドリフト（将来の検証ツールで RULE-004 ERROR 化）。

**なぜ論点か（FND-101 の目的と逆行）**:
- FND-101 は「resolved FND の double-edge が検証グラフにノイズを生む＝警告慣れ」を是正する目的だった。しかし MINOR バンプは double-edge を消す代わりに **101 件の新規ドリフト警告**を生み、警告ノイズを増やす副作用を持つ。
- 補強事実：reconciliation は A-1 で新規追加した 5 件の backref を「MINOR だと依存元ドリフトが発生する」として **z バンプに自己訂正**した（DD-8 §4「backref 追加→z バンプ」）。同じ理屈が FND ノード本体の MINOR バンプにも当てはまる。
- 補強事実：Q-3→O-1/O-2 の affects 辺（ref "0.2" 凍結）も「指摘時記録は凍結＝ドリフトさせない」運用で、provenance 辺をドリフト対象外と見なす思想と整合する。
- 補強事実：既存 main の 103 ドリフトにも MOD-1→FND-96（ref 0.3/badge 0.5）等の backref→FND ドリフトが含まれ、本問題は以前から潜在していた。

**選択肢（排他でない・組合せ可）**:
- **A（FND 辺逆転を z バンプに変更）** — 75 FND を vX.(Y+1).0 → vX.Y.(Z+1) に再バンプ（例 0.2.0→0.1.1）。x.y 不変で 101 件の新規ドリフトが消える。最小で FND-101 の目的を達成。トレードオフ＝DD-8 §4「辺削除→MINOR」と FND-96 先例（MINOR）に反するため、DD-8 に「resolved-FND lifecycle 辺逆転は z（downstream 無影響）」の例外を明文化する必要がある。75 ノードの改訂理由（MINOR と記載）も z に修正する。
- **B（MINOR 維持＋全 backref の ref_version を同期）** — 101 件の backref ref を新 badge x.y へ更新しドリフト解消。トレードオフ＝編集 101 件・かつ「全 backref 保持者が FND を再レビューした」という実体のない更新になり、ref_version の意味（指摘時/レビュー時の版）を壊す。
- **C（MINOR 維持＋ドリフトを許容ノイズとする）** — main 既存 103 と同様に放置。トレードオフ＝FND-101 の警告慣れ問題を悪化させる。
- **D（根本対処：SPEC-9/RULE-004 で backref/provenance 辺をドリフト対象外に）** — drift 判定から「resolved FND への backref」「affects/provenance 辺」を除外する。新規 101＋既存の同種も一掃。版バンプ論争（A/B/C）自体が無意味化する利点。トレードオフ＝SPEC-9 改訂＋`_drift()` 実装変更＋テスト追加が必要でスコープが大きく、実装フェーズ寄りになる。

**推奨**: **D を本筋・A を暫定**。
- 根本原因は「provenance/backref 辺をドリフト判定にかけていること」。drift の意味論は「参照先が変わったら参照元は再レビュー」だが、backref 保持者は FND の resolved 状態に依存しないため、ドリフトは純ノイズである。D で除外するのが原理的に正しく、FND-101 を真に達成する（PR2 機械判定の対象を正しく定義する／単一責務）。
- ただし D は SPEC-9 改訂＋コード改修でスコープが大きく実装フェーズ寄り。直近は **A（z バンプ）で新規ノイズを止め、D を別途 DD 化して SPEC-9 に反映する二段**が現実的。
- B は ref_version の意味を壊すため非推奨、C は警告慣れを悪化させるため非推奨。

**影響範囲**:
- **A 採用時**: 75 FND を z バンプへ再改訂（改訂理由を MINOR→z へ修正）。DD-8 §4 に「resolved-FND lifecycle 辺逆転は z（downstream 無影響）」の例外を明文化（DD-8 を改訂・該当 FND に `→DD-8` 反映を検討）。101 件の新規 backref ドリフトが解消。
- **D 採用時**: SPEC-9（RULE-004）を「backref/provenance 辺（resolved FND への被参照辺・affects 辺等）をドリフト判定対象外」とするよう改訂し、`docidx/query.py` `_drift()` の実装変更＋テスト追加。新規 101＋既存同種ドリフトを一掃。SPEC-9 改訂は接続規則ではなく判定規則の変更だが、ドリフト意味論の変更として 01-doc-verify.md・関連スキル/エージェントへの周知を要する。
- いずれも FND-101（本是正の親）の目的達成度に直結する。

**ブロッカー**: 採否（A/B/C/D の組合せ）・スコープ・実施スプリントは**オーナー判断**。実害（将来の検証ツールでの RULE-004 ERROR 化）は顕在化前のため、今スプリント実施 vs 次スプリント以降のいずれもありうるが、**独断でのスプリント繰越は禁止**（CLAUDE.md「スケジュール独断禁止」）。本 Q は `scheduled` を空のままとし、判断を仰ぐ。決定後は DD へ昇格（id 通貫）。
