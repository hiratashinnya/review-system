---
name: bloom-model-tier
description: Assign a Claude model tier + effort level to a sub-agent's frontmatter (`model:`/`effort:`) by classifying its dominant Bloom's-revised cognitive level AND whether its difficulty is thoroughness-bound or judgment-bound (Remember→haiku; Understand/Apply→sonnet; Analyze/Evaluate/Create→sonnet+high/xhigh effort if thoroughness-bound, else opus). Use when deciding which model/effort a custom agent should run on. NOT runtime control-flow (orchestration-design), NOT prompt template design (prompt-design).
---

# bloom-model-tier — Bloom 認知分類 × 難所の性質でエージェントの model/effort を選ぶ

カスタムエージェントの `model:`（＋`effort:`）を **2軸**で機械判定する：
① その仕事の主要な認知負荷（Bloom 改訂版分類の何段か）
② その難所が **網羅性ボトルネック**（thinking budget を増やせば直接品質が上がる）か **判断ボトルネック**（曖昧な解釈・利害trade-off・不可逆な決定＝モデル自体の知識/判断力が効く）か。

`effort:`（`low/medium/high/xhigh/max`・`model:` と独立に指定可）を使い、**Lv4 以上でも網羅性ボトルネックなら opus に上げず `sonnet` + 高 effort に倒す**（過剰な opus 割当のコスト規律）。
原則：spec-principles（PR2 機械判定と運用ルールを混ぜない）。

## 判定ルール（機械ゲート）

### 軸1：Bloom Lv（認知行為の種類）
| Bloom Lv | 認知行為 | 典型タスク |
|---|---|---|
| **1 記憶** | 想起・参照・転記 | 既知値の検索／定型コピー |
| **2 理解** | 説明・要約・言い換え | 内容の要約／分類タグ付け |
| **3 応用** | 適用・実行 | 確定テンプレへの当てはめ／手順実行 |
| **4 分析** | 分解・関連付け・差分検出 | 構造分解／カバレッジ点検／gap 検出 |
| **5 評価** | 判定・検証・批評 | 整合調停／監査／レビュー |
| **6 創造** | 新規生成・設計 | 要件/設計の新規著作／DFD 構築 |

### 軸2：難所の性質（Lv4 以上でのみ判定）
- **網羅性ボトルネック**：やることはルールベース／機械的だが、見落とさず全部拾う・照合することが難所。effort を増やせば直接品質が上がる（例：ledger 突合、孤立ノード検出、チェックリスト照合）。多くは「報告のみ・裁定は人間/呼び出し元に委ねる」設計。
- **判断ボトルネック**：曖昧な入力の解釈・利害/trade-off の裁定・前例のない構造の創出・不可逆な決定が難所。effort を増やしても解決しない（モデル自体の知識/判断力が効く）。多くは「推奨・裁定まで担う」設計。

### 閾値表
| Bloom Lv | 網羅性ボトルネック | 判断ボトルネック |
|---|---|---|
| 1 記憶 | `haiku` | — |
| 2 理解／3 応用 | `sonnet`（`effort: low`〜`medium`） | `sonnet`（`effort: medium`・稀） |
| 4 分析 | **`sonnet` + `effort: high`〜`xhigh`** | `opus` |
| 5 評価 | **`sonnet` + `effort: high`〜`xhigh`**（機械的チェックリスト照合・裁定なしの gap 提示） | `opus`（trade-off 裁定・受け入れ判定・新規vs既存の拡張可否判断） |
| 6 創造 | **`sonnet` + `effort: high`**（確定テンプレへの流し込みが主体の著作） | `opus`（曖昧な入力からの新規構造化・利害調整） |

太字＝旧版（Lv4以上一律 opus）から広がった sonnet 領域。

## 手順

1. 対象エージェントの `description` と system prompt から、主要行為を1つ取り出す。
2. その動詞を Bloom 段に同定（最も高い段ではなく、仕事の大半を占める段を採る）。
3. Lv4 以上なら軸2を判定：「effort（考える回数/深さ）を増やせば結果が良くなるタイプの難しさか？」→ Yes＝網羅性ボトルネック、No（解釈の余地・利害調整・裁定・不可逆決定が絡む）＝判断ボトルネック。
4. 上表で `model:`（＋Lv4以上かつ網羅性ボトルネックなら `effort:`）を確定し、frontmatter に書き込む。
5. 既存の `model:` 値と差があれば理由付きで提案し、既存値は勝手に上書きしない。

## 判定基準（タイブレーク）
- 複数段にまたがる：成果物を出すために必須な最上位の行為で採る。
- 「著作」は中身で割る：確定入力を型へ転記するだけ＝Apply(3)→sonnet。利害・制約から新規に文章/構造を構成＝Create(6)→判断ボトルネック→opus。
- 「報告のみ・裁定はしない」は網羅性側の強いシグナル：gap リスト提示やチェックリスト照合のように裁定を人間/呼び出し元に委ねる設計は、読み取り専用でも Analyze/Evaluate の網羅性ボトルネック＝`sonnet`+`xhigh` 候補。逆に「推奨・裁定」まで担うエージェントは判断ボトルネック＝opus 継続。
- 迷ったら軸2は判断ボトルネック側（opus）に倒す（effort は品質を保証しない代理変数のため安全側に倒す）。

## done

- [ ] 主要認知行為を1つに同定し、Bloom 段と動詞を明記したか。
- [ ] Lv4 以上は軸2（網羅性/判断ボトルネック）を明記したか。
- [ ] 表で `model:`／`effort:` を機械的に引いたか。
- [ ] 既存値との差分を理由付きで提示し、無断上書きしていないか。
- [ ] 判定根拠を1行（行為→Lv→軸2→model/effort）で残したか。
