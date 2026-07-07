**検証手法**: spec-inspector（自動点検）＋メインスレッドによる裏取り。
**実施日**: 2026-06-11
**対象範囲**: doc-system/01-why〜03-analysis（VAL / SR / FR / NFR / SPEC / ACTOR / I / O / D / P / E）。各層の代表ノード（VAL-1・FR-1・SPEC-1・ACTOR-1・I-1・P-1・E-1）を検証アンカーとして紐づけた。
**結果**: 指摘あり（ERROR 1・WARNING 4・INFO 1）。

構造ルール群（ref_version ドリフト＝RULE-004、`kind`/`status` 残存、リスト記法の `to:`、存在しない ID 参照＝RULE-007、階層親不在）はいずれも新エッジモデルに準拠しており、致命的な構造破壊は検出されなかった。検出された指摘は系境界・粒度・網羅性・要件本文の記述ドリフトに関するもので、いずれも意味モデル上の論点である。

**発生した指摘**: → FND-1〜FND-6 を参照。

## 凍結時点の参照記録（out-of-graph・#118 suppress 廃止に伴う記録）

本ノードはかつて `suppress: [RULE-004]` により drift 判定を凍結免除されていた（DD-2）。issue #118
で抑制機構自体が廃止されたため、以下の関連辺は edges から除去し、参照していた事実のみ本記録として
保持する。

```yaml
- to: "verify-の-rule-004-免除・fnd-は再検証シグナルとして据え置き-q-1-から昇格"
  ref_version: "0.1"
- to: "分析層の版上げに伴う-ref_version-ドリフト群-記録・義務辺含む・rule-004-warning"
  ref_version: "0.1"
```
