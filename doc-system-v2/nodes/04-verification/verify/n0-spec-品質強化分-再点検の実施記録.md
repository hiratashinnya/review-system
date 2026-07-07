**検証手法**: メインスレッドによる全 doc-system ノードの自動整合走査（id/edge 抽出スクリプト）＋目視裏取り。
**実施日**: 2026-06-12
**対象範囲**: requirements 層の SPEC 品質強化バッチ（FR-11 改訂・FR-13/14 新設・SPEC-1/2/26/27 書き直し・SPEC-31〜40 新規・condition 語彙 empty・パース検証 RULE-023〜027）を重点に、全層（VAL/SR/FR/NFR/SPEC/ACTOR/I/O/D/P/E/VERIFY/FND/DD/PEND）の参照整合・ref_version・カバレッジ・FND バックリファレンス対称性を点検。

**結果（重点バッチ）**: 合格。新規/改訂ノードについて、
- (a) FR への依存辺は全て実在・ref_version="0.2" 一致、
- (b) SPEC→親 SPEC 辺なし（全て FR 直参照）、
- (c) FR-11/13/14 のカバレッジ（normal＋failure）充足、FR-9/10/12/14 の normal 単独は suppress[RULE-018]/scheduled:post-mvp で説明可、
- (d) condition 語彙は normal/boundary/empty/failure/error に収まり empty は SPEC-31 のみで正用、
- (e) FND-12〜15 のバックリファレンス（FR-1→FND-12・SPEC-31→FND-13・SPEC-1/2/26/27→FND-14・FR-11→FND-15）対称。

**SPEC 品質強化バッチに新規ギャップなし**。

**結果（全グラフ走査の副次発見）**: 既存層に整合崩れを検出 → FND-16（RULE-007 ERROR）・FND-17（RULE-004 ドリフト群 WARNING）・Q-1（凍結記録のドリフト扱いの設計論点）を起票。

**発生した指摘**: → FND-16・FND-17・Q-1 を参照。

## 凍結時点の参照記録（out-of-graph・#118 suppress 廃止に伴う記録）

本ノードはかつて `suppress: [RULE-004]` により drift 判定を凍結免除されていた（DD-2）。issue #118
で抑制機構自体が廃止されたため、以下の関連辺は edges から除去し、参照していた事実のみ本記録として
保持する。

```yaml
- to: "verify-の-rule-004-免除・fnd-は再検証シグナルとして据え置き-q-1-から昇格"
  ref_version: "0.1"
- to: "分析層の版上げに伴う-ref_version-ドリフト群-記録・義務辺含む・rule-004-warning"
  ref_version: "0.1"
- to: "凍結記録-verify・解消済み-fnd-の-ref_version-ドリフト扱い"
  ref_version: "0.1"
```
