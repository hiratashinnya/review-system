---
name: bloom-model-tier
description: Assign a Claude model tier to a sub-agent's frontmatter `model:` field by classifying its dominant Bloom's-revised cognitive level (Remember→haiku, Understand/Apply→sonnet, Analyze/Evaluate/Create→opus). Use when deciding which model a custom agent should run on. NOT runtime control-flow or version-stamp logging (orchestration-design), NOT prompt template design (prompt-design).
---

# bloom-model-tier — Bloom 認知分類でエージェントの model を選ぶ

カスタムサブエージェントの `model:` を、その仕事の**主要な認知負荷**（Bloom 改訂版分類の何段か）で機械判定する。
原則：[spec-principles](../spec-principles/SKILL.md)（**PR2 機械判定と運用ルールを混ぜない**＝Bloom レベルは順序ある属性なので自動ゲート可能・**PR7 矛盾は停止**）。

## 判定ルール（機械ゲート＝PR2）

エージェントの**主要認知行為**を Bloom 改訂版（順序属性）の1段に同定し、下表で `model:` を引く。

| Bloom Lv | 認知行為（動詞） | 典型タスク | `model:` |
|---|---|---|---|
| **1 記憶** Remember | 想起・参照・転記 | 既知値の検索／定型コピー／単純抽出 | **`haiku`** |
| **2 理解** Understand | 説明・要約・言い換え | 内容の要約／分類タグ付け／読み解き | **`sonnet`** |
| **3 応用** Apply | 適用・実行 | 確定テンプレへの当てはめ／手順実行／定型変換 | **`sonnet`** |
| **4 分析** Analyze | 分解・関連付け・差分検出 | 構造分解／カバレッジ点検／矛盾・gap 検出 | **`opus`** |
| **5 評価** Evaluate | 判定・検証・批評 | 整合調停／監査／レビュー／受け入れ判定 | **`opus`** |
| **6 創造** Create | 新規生成・設計 | 要件/設計の新規著作／DFD 構築／戦略立案 | **`opus`** |

**閾値**：`Lv1 → haiku` ／ `Lv2–3 → sonnet` ／ `Lv4 以上 → opus`。

## 手順
1. 対象エージェントの `description` と system prompt から、**結論を出すために繰り返す主要行為**を1つ取り出す（補助的な下位行為に引っ張られない）。
2. その行為の動詞を上表の Bloom 段に同定（**最も高い段ではなく、仕事の大半を占める段**を採る）。
3. 閾値で `model:` を確定し、frontmatter に書き込む（`model: opus` 等）。
4. 既存の `model:` 値と差があれば**理由付きで提案**し、既存値は**勝手に上書きしない**（PR8 消さない/壊さない・特に `inherit` 統一が意図的規約の場合）。

## 判定基準（タイブレーク）
- **複数段にまたがる**：成果物を出すために必須な最上位の行為で採る（例：点検しつつ提案＝Evaluate→opus）。ただし上位行為が**例外的・補助的**なら主行為を採る。
- **「著作」は中身で割る**：確定入力を型へ**転記**するだけ＝Apply(3)→sonnet。利害・制約から**新規に文章/構造を構成**＝Create(6)→opus。
- **読み取り専用でも opus はあり得る**：監査・点検は生成しなくても Analyze/Evaluate なので opus。
- **迷ったら低い段**に倒し、根拠を1行残す（過剰な opus 割当を避ける＝コスト規律）。`inherit` 維持も正当な選択。

## done（点検観点）
- [ ] 主要認知行為を1つに同定し、Bloom 段と動詞を明記したか。
- [ ] 閾値（1/2-3/4+）で `model:` を機械的に引いたか（恣意的選定でないか）。
- [ ] 既存値との差分を理由付きで提示し、無断上書きしていないか。
- [ ] 判定根拠を1行（行為→段→model）で残したか（後から追える）。

## 成果物テンプレ

**単体（frontmatter 提案）**
```yaml
model: opus   # Bloom Lv5 評価（横断点検し gap/矛盾を判定）→ 閾値 4+ → opus
```

**一覧（複数エージェントの分類表）**

| agent | 主要認知行為 | Bloom Lv | 推奨 `model:` | 現状 |
|---|---|---|---|---|
| `<name>` | <動詞・1語> | <1–6 段名> | `haiku`/`sonnet`/`opus` | `inherit` 等 |
