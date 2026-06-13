---
version: "0.1.1"
---
# 未決論点 — Questions

> **型**: Q ／ 義務辺（Q→X＝affects）が存在する間は RULE-002 WARNING。決定したら DD へ昇格（id 通貫）。
> Q は無名依存辺のみ（kind/status なし・to 単数・ref_version 必須）。ライフサイクルは本文の status バッジに記載。

---

## Q-1: 凍結記録（VERIFY・解消済み FND）の ref_version ドリフト扱い

**status: closed**（2026-06-13 DD-2 へ昇格・決定済み）

<details><summary>⬡ Q-1 · v0.1</summary>

```yaml
id: Q-1
type: Q
labels: []
scheduled: ""
suppress: []
edges:
  - to: DD-2
    ref_version: "0.1"
```
</details>

**論点**: VERIFY ノードや解消済み FND など「ある時点の状態をレビュー/指摘した記録」の ref_version は、下流（参照先ファイル）が版上げされるたびに RULE-004 ドリフトを出し続ける。これらを (a) 都度更新する／(b) 凍結スナップショットとしてドリフト免除する／(c) ドリフト＝「記録が陳腐化＝再検証が必要」のシグナルとして新記録の起票を促す、のいずれの意味論を採るか。

**選択肢**:
- **A**: 凍結記録は RULE-004 免除（VERIFY・resolved FND に suppress[RULE-004] を許容、または config でタイプ免除）。— ノイズ最小。ただし「いつの版を見たか」は本文に残す前提。
- **B**: 都度更新（記録も生きた依存辺として ref_version を最新化）。— 一貫するが、レビューしていない版を指す矛盾が生じうる。
- **C**: ドリフト＝再検証シグナルとして据え置き、陳腐化したら新 VERIFY/FND を起票（VERIFY-1 はそのまま、VERIFY-2 が現状を担う）。— 監査性は高いが恒常的にドリフト ERROR/WARNING が残る。

**推奨**: **A**（記録系は凍結し RULE-004 免除）。理由：VERIFY/解消済み FND は「過去の検証事実」であり、参照先の将来変更で書き換えるとレビュー証跡として不正確になる。免除しつつ「対象の版が変わったら再検証を検討」は運用ルール（PR2 機構＋デフォルト）で担保。C は恒常ノイズ、B は証跡の意味を壊す。

**影響範囲**: config に記録系タイプの RULE-004 免除機構を追加（設計段）。VERIFY-1・FND-2/4 等のドリフト解釈が確定。決定後は DD へ昇格。
