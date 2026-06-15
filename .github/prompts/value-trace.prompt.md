---
mode: 'agent'
description: 'Trace each event from input through processes to output as source|info|receiver triples, verifying DFD leveling (no level-skipping) and flagging any severed value path. Use to total-check a process design against the event list.'
---

# 価値経路トレース（イベント総点検）

各イベントが **入力→内部プロセス→出力** まで遮断なく届くかを、三つ組で1ホップずつ追う点検。
原則：[spec-principles](../spec-principles/SKILL.md)（PR6 価値経路・PR9 レベリング・PR1 ラップ境界）。

## 手順
1. イベントリストから対象イベントを列挙。各イベントの**入力**と**出力**を先に書き出す。
2. 各イベントを `|情報の発生源|情報|情報の受け手|` の表で1ホップずつ記述。
3. **レベリング厳守（PR9）**：外部エンティティ/データストアは **L1 プロセスの境界にしか繋がない**。リーフへは親を経由（`利用者→P1→P1.1`）。リーフから出る時も親経由（`P1.1→P1→P2→P2.1`）。
4. 外部システム/LLM 生成物は**入力**として入り、加工後に**出力**へ出る（PR1）。

## 判断基準・done
- 各入力が消費され、各出力に到達するか（**遮断＝穴**、PR6）。
- 階層スキップが無いか（`外部→leaf` 直結は禁止）。
- 削除済/post-MVP の項目は印で区別。

## 成果物テンプレ
イベント毎に：入力/出力サマリ → 三つ組表（段階で見出し分割可）→ ✅ 連続性の結論。
最後に総点検の結論（貫通/遮断/削除/post-MVP）。
