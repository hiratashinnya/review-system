---
version: "0.1.0"
---
# 論理プロセス

> **型**: P ／ **必須上流**: SPEC（refines ✅）
> I→P は P 側が `kind: consumes`、E→P は E 側が `kind: triggers`（I/E 側には書かない）。

---

## P1: 受付・正規化

<details><summary>⬡ P-1 · v0.1</summary>

```yaml
id: P-1
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: I-1
    kind: consumes
    status: pending
    ref_version: "0.1"
  - to: I-2
    kind: consumes
    status: pending
    ref_version: "0.1"
  - to: O-14
    kind: produces
    status: pending
    ref_version: "0.1"
```
</details>

提出物（I-1）と型上書き（I-2）・型推定（I-15、post-MVP）を受け取り、「対象集合・参照集合・確定 doc_type・scope」に正規化して後段（P-2・P-3）に渡す。空文書は no-op で終了。型確定は I-2 優先・I-15 でフォールバック（P1.1 調停）。

---

## P2: 基準合成

<details><summary>⬡ P-2 · v0.1</summary>

```yaml
id: P-2
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-4
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: I-4
    kind: consumes
    status: pending
    ref_version: "0.1"
  - to: I-5
    kind: consumes
    status: pending
    ref_version: "0.1"
  - to: O-14
    kind: produces
    status: pending
    ref_version: "0.1"
```
</details>

確定した doc_type × scope に対応する観点ファイル群（I-4）を継承・union 合成し、観点パック＋メタ表を毎回生成して P-3・P-4 に渡す。基準パース失敗は fail-close → O-14。衝突/矛盾/方向逸脱は O-9 警告（合成時に毎回チェック）。

---

## P3: 評価（AI 指摘生成）

<details><summary>⬡ P-3 · v0.1</summary>

```yaml
id: P-3
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-6
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: O-14
    kind: produces
    status: pending
    ref_version: "0.1"
```
</details>

観点パックと評価対象からプロンプトを組み立て PF（ACTOR-4）を呼び出し、findings / unmatched を取得する。LLM 障害は bounded retry 後 fail-close → O-14。生 findings は後段（P-4）へ渡す（素通し出力禁止）。

---

## P4: 検証・仕分け

<details><summary>⬡ P-4 · v0.1</summary>

```yaml
id: P-4
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-8
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: SPEC-9
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: I-5
    kind: consumes
    status: pending
    ref_version: "0.1"
```
</details>

P-3 からの生 findings を rule_id 検証・ポリシー（I-5）参照で検証し、🤖（自動修正）/ ✋（要承認）/ 💬（要判断）に仕分ける。rule_id 未付与は ❓ 未分類（O-7）へ退避。仕分け済み results を P-5 へ渡す。

---

## P5: 適用・レポート

<details><summary>⬡ P-5 · v0.1</summary>

```yaml
id: P-5
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-10
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: SPEC-11
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: SPEC-12
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: SPEC-13
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: SPEC-14
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: I-6
    kind: consumes
    status: pending
    ref_version: "0.1"
  - to: I-14
    kind: consumes
    status: pending
    ref_version: "0.1"
  - to: O-1
    kind: produces
    status: pending
    ref_version: "0.1"
  - to: O-3
    kind: produces
    status: pending
    ref_version: "0.1"
  - to: O-4
    kind: produces
    status: pending
    ref_version: "0.1"
  - to: O-5
    kind: produces
    status: pending
    ref_version: "0.1"
  - to: O-6
    kind: produces
    status: pending
    ref_version: "0.1"
  - to: O-7
    kind: produces
    status: pending
    ref_version: "0.1"
```
</details>

仕分け済み results を元に自動適用（P5.2）・レポート生成（P5.3）・revert（P5.4）を担う。
🤖 の自動適用は上流（P3/P4）がクリーン完了した場合のみ実行（SPEC-14）。finding 単位コミット（DS3）。
レビュアーの承認・決定（I-6）を受けて ✋/💬 の人手適用も行う。

---

## P6: 育成・ガバナンス

<details><summary>⬡ P-6 · v0.1</summary>

```yaml
id: P-6
type: P
labels: [post-mvp]
scheduled: "p3"
edges:
  - to: SPEC-10
    kind: refines
    status: pending
    ref_version: "0.1"
  - to: I-7
    kind: consumes
    status: pending
    ref_version: "0.1"
```
</details>

「対象外」フラグ（I-7）・却下傾向を蓄積（DS5）し、観点 FB 提案（O-12）・基準ひな形（O-11）・合成時警告（O-9）を ACTOR-3 に提供する。育成ループの閉路：現場傾向→提案→系外編集→次回合成。（MVP は最小実装）
