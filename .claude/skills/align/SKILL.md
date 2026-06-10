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

## doc-system ノード著作（VAL / SR）
価値の根を据えるこの段で **Why 層**ノードを著作する。共通手順・横断スパイン（DD/Q/PEND/VERIFY/FND）・RULE 全文・本文フォーマットは [07-authoring-guide.md](../../../docs/doc-system/07-authoring-guide.md)。スキーマ→[02-meta-schema.md](../../../docs/doc-system/02-meta-schema.md)、接続要否→[03-connection-matrix.md](../../../docs/doc-system/03-connection-matrix.md)。

| 型 | 必須辺 | 主な RULE |
|---|---|---|
| VAL | なし（根） | RULE-005（孤立禁止）|
| SR | → VAL (refines) | RULE-006 |
