# N5（P 単一責務点検）— VERIFY-3 / FND-19 / FND-20

> verification-author 出力。reconciliation が検証後に本ファイルへ反映する。
> 反映先: VERIFY-3 → `doc-system/04-verification/01-doc-verify.md` ／ FND-19・FND-20 → `doc-system/04-verification/02-findings.md`
> 無名依存辺のみ（`kind`/`status` なし・`to` は単数・全辺に `ref_version` 必須）。

---

## 反映先 1: `doc-system/04-verification/01-doc-verify.md`（VERIFY-3）

VERIFY-2 の直後（L99 以降）に追記する。

```markdown

---

## VERIFY-3: N5（P 単一責務点検）の実施記録

<details><summary>⬡ VERIFY-3 · v0.1</summary>

```yaml
id: VERIFY-3
type: VERIFY
labels: []
scheduled: ""
suppress: [RULE-004] # 過去の検証事実スナップショット。参照先の版上げによるドリフトは凍結免除（DD-2）
edges:
  - to: P-1
    ref_version: "0.6"
  - to: P-4
    ref_version: "0.6"
  - to: P-5
    ref_version: "0.6"
  - to: P-6
    ref_version: "0.6"
  - to: P-7
    ref_version: "0.6"
  - to: DD-2
    ref_version: "0.1"
```
</details>

**検証手法**: メインスレッドによる P ノードの単一責務点検（DFD レベリング規律 PR9・本文責務記述と対応 SPEC の突合）。
**実施日**: 2026-06-13
**対象範囲**: processes.md v0.6.3 の P-1（受付・パース）・P-4（レポート生成）・P-5（設定ファイル読み込み）・P-6（in-graph 集合決定）・P-7（ノード著作プロセス）。P-2/P-3 は N0〜N1 で既に分解済み（FND-2/FND-4）のため本回の対象外。

**各 P の判定**:
- **P-1「受付・パース」**: パース段検証（RULE-023〜028）の責務が本文の責務記述に含まれず、対応 SPEC（SPEC-2/32/33/34/35/52/53）がどの P からも参照されない無主状態 → 価値経路の上流欠落（PR6）→ **FND-20**。
- **P-4「レポート生成」**: 整列・整形・出力・終了コードは出力側の単一データフローを成し、責務分割の必要なし → **単一責務 PASS**。
- **P-5「設定ファイル読み込み」**: config 取り込みの単一責務 → **PASS**。
- **P-6「in-graph 集合決定」**: trace_scope 照合による in-graph 集合決定の単一責務 → **PASS**。
- **P-7「ノード著作プロセス」**: (1) 著作（agent→tmp）と (2) 調停（reconciliation→本ファイル）の2活動を1プロセスに内包し、別アクタ・別段階のため単一責務違反（PR9）→ **FND-19**。

**結果**: 指摘 2 件（WARNING 2＝FND-19・FND-20）。P-4/P-5/P-6 は単一責務 PASS。

**発生した指摘**: → FND-19・FND-20 を参照。
```

---

## 反映先 2: `doc-system/04-verification/02-findings.md`（FND-19・FND-20）

FND-18 の直後（L446 以降）に追記する。

```markdown

---

## FND-19: P-7「ノード著作プロセス」の単一責務違反（著作＋調停の2活動内包）

<details><summary>⬡ FND-19 · v0.1</summary>

```yaml
id: FND-19
type: FND
labels: []
scheduled: ""
edges:
  - to: P-7
    ref_version: "0.6"
```
</details>

**深刻度**: WARNING
**内容**: P-7「ノード著作プロセス」が次の2活動を1プロセスに内包している。
- (1) **著作**: 仕様著者（ACTOR-1）＋著作エージェントが `tmp/<sprint>/<id>.md` に草案を出力する活動（SPEC-38・E-2 トリガ）。
- (2) **調停**: reconciliation エージェントが tmp を検証し本ファイルへ転記し O-3 を生成する活動（SPEC-39）。

別アクタ（著作エージェント vs reconciliation エージェント）・別段階（草案 vs 確定）であり、DFD レベリング上の単一責務違反（PR9）。対応 SPEC-38/39 も別責務に対応しており、1プロセスに束ねるのは粒度過大。
**対応状況**: resolved
**対応内容**: DFD レベリングで P-7 を **P-7-1**（著作・tmp 出力・SPEC-38）と **P-7-2**（調停・本ファイル反映・SPEC-39）に分解した。O-3 の生成元辺を P-7→P-7-2 に張替え。P-7 に `→FND-19` バックリファレンス辺を付与済み（processes.md v0.6.3→0.6.4・io.md v0.6.5→0.6.6）。
**指摘時 ref_version**: P-7 "0.6"（processes.md v0.6.3 時点）

---

## FND-20: P-1「受付・パース」にパース段検証（RULE-023〜028）の責務記述がなく対応 SPEC が無主

<details><summary>⬡ FND-20 · v0.1</summary>

```yaml
id: FND-20
type: FND
labels: []
scheduled: ""
edges:
  - to: P-1
    ref_version: "0.6"
```
</details>

**深刻度**: WARNING
**内容**: P-1「受付・パース」は構造化ノードセットを生成するが、本文の責務記述にパース段検証（RULE-023〜028）が含まれていない。対応する SPEC-2（RULE-023）・SPEC-32（RULE-024）・SPEC-33（RULE-025）・SPEC-34（RULE-026）・SPEC-35（RULE-027）・SPEC-52（スキーマ適合）・SPEC-53（RULE-028）が、どの P からも参照されない無主状態であり、FR/SPEC の裏付けを持つ機能が分析層のプロセスに接続されていない＝価値経路の穴（PR6）。P-1 はパース処理そのものを担うため、これらパース段検証は P-1 の単一責務（パース段処理）に含めるのが妥当である。
**対応状況**: resolved
**対応内容**: P-1 の責務記述を「パース＋パース段検証（RULE-023〜028）」に明確化し、SPEC-2/32/33/34/35/52/53 への依存辺を P-1 に追加した（P-2-2 が複数 RULE を1責務で持つのと同様、パース段処理は単一責務として保持し分解しない）。P-1 に `→FND-20` バックリファレンス辺を付与済み（processes.md v0.6.3→0.6.4）。なお SPEC-31（empty・in-graph 0 件）はパースではなく in-graph 集合決定/オーケストレーションの責務のため P-1 には含めず、別途 P-6/orchestration の論点として残す。
**指摘時 ref_version**: P-1 "0.6"（processes.md v0.6.3 時点）
```
