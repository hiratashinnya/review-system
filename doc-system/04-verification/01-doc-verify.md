---
version: "0.1.0"
---
# ドキュメント検証 — doc-system ドッグフーディング（要件〜分析層）

> **型**: VERIFY ／ **必須**: 対象要素への依存辺が1本以上（RULE-006 config: `must_link_to: VERIFY → any`）
> 無名依存辺のみ（`kind`/`status` なし・`to` は単数・全辺に `ref_version` 必須）。

---

## VERIFY-1: 要件〜分析層の spec-inspector レビュー

<details><summary>⬡ VERIFY-1 · v0.1</summary>

```yaml
id: VERIFY-1
type: VERIFY
labels: []
scheduled: ""
edges:
  - to: VAL-1
    ref_version: "0.2"
  - to: FR-1
    ref_version: "0.2"
  - to: SPEC-1
    ref_version: "0.3"
  - to: ACTOR-1
    ref_version: "0.2"
  - to: I-1
    ref_version: "0.4"
  - to: P-1
    ref_version: "0.4"
  - to: E-1
    ref_version: "0.4"
```
</details>

**検証手法**: spec-inspector（自動点検）＋メインスレッドによる裏取り。
**実施日**: 2026-06-11
**対象範囲**: doc-system/01-why〜03-analysis（VAL / SR / FR / NFR / SPEC / ACTOR / I / O / D / P / E）。各層の代表ノード（VAL-1・FR-1・SPEC-1・ACTOR-1・I-1・P-1・E-1）を検証アンカーとして紐づけた。
**結果**: 指摘あり（ERROR 1・WARNING 4・INFO 1）。

構造ルール群（ref_version ドリフト＝RULE-004、`kind`/`status` 残存、リスト記法の `to:`、存在しない ID 参照＝RULE-007、階層親不在）はいずれも新エッジモデルに準拠しており、致命的な構造破壊は検出されなかった。検出された指摘は系境界・粒度・網羅性・要件本文の記述ドリフトに関するもので、いずれも意味モデル上の論点である。

**発生した指摘**: → FND-1〜FND-6 を参照。
