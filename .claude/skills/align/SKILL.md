---
name: align
description: Pre-work alignment. Decompose the request, propose the steps and granularity, ask the open questions, and declare the fixed parameters before starting. Use before any multi-step design task.
---

# 認識合わせ（着手前の段取り）

重い作業の前にゴール・手順・粒度・前提・停止条件を握る。
原則：[spec-principles](../spec-principles/SKILL.md)（PR10 認識合わせ先行・PR7 矛盾は停止）。

## 手順
1. 依頼を分解し、**作業手順を提案**（成果物と粒度を明示）。
2. 結果を変える**不明点・選択肢を質問**（AskUserQuestion）。変えないものは既定で進めると宣言。
3. **確定パラメータ**（スコープ・進め方・停止条件＝矛盾は打ち上げ）を宣言してから着手。

## done
- 手順・スコープ・停止条件が明文化され合意されているか。
- 既存資料を過信しない前提（点検も兼ねる）を共有したか。

## ノード著作（VAL / SR）

**共通手順**
1. テンプレ複製：`docs/doc-system/templates/why/<type>.md`
2. id 採番：`PREFIX-N`（連番・永続・変更禁止）、既存最大 +1
3. 必須 edges を追加（下表）。`to` が実在する id か確認（RULE-007: always_error）
4. status: pending から始め、反映確認後に done
5. ref_version を参照先の現在 `x.y` に合わせる
6. 受け入れ条件を確認（下表）

| 型 | 必須辺 | 主な RULE |
|---|---|---|
| VAL | なし（根） | RULE-005（孤立禁止）|
| SR | → VAL (refines) | RULE-006 |

**本文フォーマット**

```
# VAL
[誰に] [何の便益をもたらすか] を1文で記述。

# SR
[ステークホルダー] が [状況] において [欲求・期待] を持つ。
```

**受け入れ条件**
- [ ] id 一意、type 一致、edges の to がすべて実在（RULE-007: always_error）
- [ ] 接続マトリクス ✅ の辺がすべて存在（RULE-006）
- [ ] see-also 辺の status が `n/a`（RULE-014）
- [ ] ref_version が参照先の現在バージョンと一致（RULE-003/004）
