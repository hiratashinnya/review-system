---
name: schema-design
description: Design a structured config/criteria file schema reader-first — list readers, use a frontmatter (machine) + body (human/LLM) two-layer split, route attributes by the two axes, and disambiguate with samples. Use when an external settings/criteria file format is needed.
---

# スキーマ設計（読み手から決める）

構造化ファイル（基準/設定）のスキーマを、読み手起点で決める。
原則：[spec-principles](../spec-principles/SKILL.md)（PR2 2軸）。

## 手順
1. **読み手を列挙**（人／プログラム／LLM 等）し、各々の欲しい形を出す。
2. **二層構成**：フロントマター（機械可読・ルーティング）＋本文（人＆LLM 共用）。
3. **属性を2軸で振り分け**（PR2）：順序ある属性＝機械が自動ゲート／事実性・妥当性＝人が確認。対応モード等の写像は別ファイル（責務分離）。
4. 継承/上書きは「具体が勝つ」機構＋権威は別レイヤ（方向ゲート）。
5. **サンプルで曖昧さを潰す**（境界条件＝多段継承・ロック・本文差し替え）。

## done
- 機械判定と運用ルールが混ざっていないか。
- サンプルで境界条件が検証できているか。
