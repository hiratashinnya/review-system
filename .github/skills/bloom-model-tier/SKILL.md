---
name: bloom-model-tier
description: Assign a Claude model tier to a sub-agent's frontmatter `model:` field by classifying its dominant Bloom's-revised cognitive level (Remember→haiku, Understand/Apply→sonnet, Analyze/Evaluate/Create→opus). Use when deciding which model a custom agent should run on. NOT runtime control-flow (orchestration-design), NOT prompt template design (prompt-design).
---

# bloom-model-tier — Bloom 認知分類でエージェントの model を選ぶ

カスタムエージェントの `model:` を、その仕事の主要な認知負荷（Bloom 改訂版分類）で機械判定する。
原則：spec-principles（PR2 機械判定と運用ルールを混ぜない）。

## 判定ルール（機械ゲート）

| Bloom Lv | 認知行為 | 典型タスク | `model:` |
|---|---|---|---|
| **1 記憶** | 想起・参照・転記 | 既知値の検索／定型コピー | **`haiku`** |
| **2 理解** | 説明・要約・言い換え | 内容の要約／分類タグ付け | **`sonnet`** |
| **3 応用** | 適用・実行 | 確定テンプレへの当てはめ／手順実行 | **`sonnet`** |
| **4 分析** | 分解・関連付け・差分検出 | 構造分解／カバレッジ点検／gap 検出 | **`opus`** |
| **5 評価** | 判定・検証・批評 | 整合調停／監査／レビュー | **`opus`** |
| **6 創造** | 新規生成・設計 | 要件/設計の新規著作／DFD 構築 | **`opus`** |

**閾値**：`Lv1 → haiku` ／ `Lv2–3 → sonnet` ／ `Lv4 以上 → opus`

## 手順

1. 対象エージェントの `description` と system prompt から、主要行為を1つ取り出す。
2. その動詞を上表の Bloom 段に同定（最も高い段ではなく、仕事の大半を占める段を採る）。
3. 閾値で `model:` を確定し、frontmatter に書き込む。
4. 既存の `model:` 値と差があれば理由付きで提案し、既存値は勝手に上書きしない。

## done

- [ ] 主要認知行為を1つに同定し、Bloom 段と動詞を明記したか。
- [ ] 閾値で `model:` を機械的に引いたか。
- [ ] 既存値との差分を理由付きで提示し、無断上書きしていないか。
- [ ] 判定根拠を1行（行為→段→model）で残したか。
