**深刻度**: WARNING

**対応状況**: resolved（本コミットで A-1＝FND-101／DD-16・DD-21 と同型の辺逆転一括是正を 19 件へ適用して同時処置・sprint-1）

**指摘時 ref_version**:（DD-3。本 FND の根拠はいずれも provenance のため backref を張らず本文記録のみとする。）
- SPEC-60-2 "0.2"（doc-system/02-what/03-spec.md の SPEC-60-2 バッジ v0.2.0 時点・`resolved` キー未設定→unresolved 判定の正本）
- DD-16 "0.1"（doc-system/04-verification/04-decisions.md の DD-16 バッジ v0.1.0 時点・fnd_lifecycle 正式化）
- DD-21 "0.1"（doc-system/04-verification/04-decisions.md の DD-21 バッジ v0.1.1 時点・backref/lifecycle 操作＝z バンプ規約）
- FND-101 "0.1"（doc-system/04-verification/02-findings.md の FND-101 バッジ v0.1.2 時点・A-1 辺逆転一括是正の先行事例）

### 内容

`doc-system/04-verification/02-findings.md` の全 110 FND を機械集計したところ、**19 件が「本文の対応状況＝resolved」でありながら YAML の `resolved: true` フラグを欠く**ことが判明した。

`fnd_lifecycle.resolved_field`（config.yaml L96＝`resolved`）の機械判定は **SPEC-60-2**（`resolved` キー未設定→既定 `false`＝unresolved）に従うため、これら 19 件は**機械判定上 unresolved に分類される**。すなわち「本文 resolved／機械 unresolved」の状態ドリフトが生じている。さらに各件は元の forward 辺（FND → 対象）を保持したままであり、resolved 化には A-1（FND-101・DD-16/DD-21）と同型の辺逆転（forward 削除 → backward 付与）が必要であった。

**対象 19 件**: FND-17, 18, 24, 25, 26, 27, 28, 31, 33, 36, 78, 84, 85, 86, 92, 93, 94, 102, 106

**除外（重要・本 FND は辺設計に一切触れない）**:
- **FND-99** … `edges: []` で「forward 辺なし」が**意図的設計**。本文に RULE-005 完全孤立を意図保持と明記済み。
- **FND-108** … `edges: []` で forward 辺なしが意図的設計。

上記 2 件は既に意図的に forward 辺を持たない設計であり、状態ドリフト 19 件には含まれない。**本 FND-111 は FND-99／FND-108 の辺設計には一切変更を加えない**。

### 深刻度判定の根拠

**WARNING**。fnd_lifecycle の両ルール（unresolved/resolved）は config 上 `activate_stage: verification` であり、現 `current_stage: design`（config.yaml L8）では**未発火**のため live な機械 RULE 失敗は発生しない。一方で「本文 resolved／機械 unresolved」のドリフトは、集計・状態整合・トレース解析で誤読を生む構造的負債であり、また forward 辺の残置は resolved FND の本来の意味（処置対象から指される＝過去指摘の証跡）に反する。live RULE 失敗を伴わない構造的ドリフトは WARNING とする先例（FND-101）に倣う。

### 是正方針（A-1 と同型・DD-16/DD-21/FND-101 準拠）

A-1（FND-101・DD-16/DD-21）と同型の辺逆転を 19 件へ適用する。各 FND に `resolved: true`＋`edges: []` を付与し、指摘時 ref_version を本文へ移動（DD-3）、in-graph 処置対象には `対象 → FND` の backward 辺を付与、provenance 辺は削除し本文記録のみとする。badge は **z バンプ**（DD-21・DD-8 §4「backref/lifecycle 操作＝z」）。

### 対応内容（本コミットで同時実施）

- 各 FND を `resolved: true`＋`edges: []` 化し、指摘時 ref_version を本文へ移動（DD-3）。
- badge を z バンプ（v0.1.0→v0.1.1。**FND-102／FND-106 は v0.2.0→v0.2.1**）。
- **in-graph 処置対象**に `対象 → FND` backref を付与（各対象も z バンプ）:
  VERIFY-1 / I-1 / FR-1 / SPEC-14-1 / SPEC-48 / FR-15 / SPEC-54 / SPEC-50 / SPEC-51 / SPEC-47 / SPEC-49 / SPEC-44 / E-1 / P-8 / P-9 / D-4 / P-2-2-3 / D-9 / D-14 / SPEC-15-1 / SPEC-8。
- **provenance 辺**（FND→DD/FND/Q：DD-5 / DD-7 / DD-8 / DD-19 / FND-18 / FND-32 / FND-79）は削除し本文記録のみとする（backref なし）。
- **FND-106** は incoming なし・処置対象が DD-19（provenance）のみのため、**意図的孤立として保持**（suppress なし・FND-37/38/99 先例）。他 18 件は既存 incoming（VERIFY/DD）または新規 backref により非孤立。

### 本 FND-111 自身の構造

- `resolved: true`・`edges: []`。本 FND の根拠（DD-16 / DD-21 / SPEC-60-2 / FND-101）はいずれも **provenance** であり、backref は張らず上記「指摘時 ref_version」に本文記録のみとする。本 FND-111 は 19 件の resolved FND 群を一括是正したメタ／監査 FND であり、単一の in-graph 処置対象を持たない（根拠はすべて provenance）ため、resolved-FND を指す backward 辺（`対象→FND-111`）の**付与先なし**であり、これは意図的孤立を正しく示すシグナルである。
- incoming も持たないため **意図的孤立として保持**（suppress なし・FND-101/37/38 先例）。なお fnd_lifecycle の両ルール（unresolved/resolved）は `activate_stage: verification` であり、現 design stage では未発火のため、RULE-005（完全孤立・always_error）以外の resolved 系ルールは発火しない。RULE-005 については処置対象がバッチ（19 件の resolved FND 群）であり単一 in-graph 処置対象を持たないため、孤立を意図的に保持する（FND-101 と同パターン）。

> **config.yaml 規則変更なし**: 本対応は既存の `fnd_lifecycle`（unresolved: forward 必須／resolved: backward 必須＋forward 不在期待）に準拠する辺逆転処置のみであり、config.yaml の `must_link_to`/`must_be_linked_from`/`fnd_lifecycle` を変更しない。よって out-of-graph 著作資産への規則伝播チェック（FND-99 パターン）は不要。
