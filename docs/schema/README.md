# 評価基準ファイル スキーマ仕様（v0 / 叩き台）

> A1「評価基準ファイルのスキーマを実際に書く」の成果物。
> サンプルで曖昧さを潰すのが目的。確定ではなく**議論のための叩き台**。
> 詳細な背景は [../requirements/01-criteria-files.md](../requirements/01-criteria-files.md) を参照。

## 設計の出発点：情報の「読み手」から決める

基準ファイルは3者に読まれる。求める形が違うので、**層を分ける**。

| 読み手 | 用途 | 欲しい形 |
|---|---|---|
| 人間 | 観点を読み書きする | 自然文の Markdown（良い例/悪い例つき） |
| プログラム | 基準の選択・継承マージ・指摘の仕分け | 機械可読な少数フィールド |
| LLM | 評価プロンプトの組み立て | 観点の説明本文（＝人間向け本文を流用） |

→ **YAML フロントマター（ルーティング層）＋ Markdown 本文（観点＝人間 & LLM 共用）** の二層構成にする。

### 役割分担（重要）

- **LLM は仕分けをしない。** 観点違反を見つけ、`rule id` を付け、修正原案を出すだけ。
- **プログラムが仕分けする。** `id → determinism × severity → ポリシー` で機械的に 🤖/✋/💬 に振り分ける。
  仕分けロジックは基準ファイルに直書きせず、別の **ポリシーファイル**（[policy.schema.md](#自動化ポリシーファイル) 参照）に置く（責務分離）。
- **LLM はもう1か所、レビュー前の基準合成でも使う。** 兄弟ファイルの本文が「矛盾しているか」だけを判定する
  整合性チェック（→ [スコープ内マージ](#スコープ内マージ同-doc_typescope-の兄弟ファイル)）。方向（厳しく/緩め）の判定には使わない。

---

## 横断概念：システムの判定基準 と 運用ルール（2軸）

この仕様を読むときの最重要レンズ。あらゆる「判定」は次の2種類のどちらか。混ぜない。

| | システムの判定基準（機械判定） | 運用ルール（人間が承認で担保） |
|---|---|---|
| 定義 | 入力が決まれば答えが一意。プログラムが自動実行・自動ゲート | 機械が方向・妥当性を判定**できない**。人がレビューして決める |
| 成立条件 | 値に**順序がある**属性（大小で「厳しく/緩め」が決まる） | プロース・事実性・妥当性（順序がない／文脈依存） |

### 属性の振り分け

| 属性 | 軸 | 機械が言えること |
|---|---|---|
| `severity`（error>warning>info） | 機械判定 | 下げる＝緩め。方向を自動判定しゲート発火 |
| 適用モード（log_only>suggest>human_only） | 機械判定 | 自動化を上げる＝リスク側。自動判定 |
| `enabled`（true→false） | 機械判定 | オフ＝緩め。自動判定 |
| `override`（locked/…/open） | 機械判定 | ゲートの強さ。発火条件 |
| **本文（観点プロース）** | **運用ルール** | 「親と差分がある」事実(diff)のみ。**厳しく/緩めは判定不能** |
| `determinism` | **運用ルール** | 変更が緩めかではなく「事実として正しいか」が問題 |
| 上書きの妥当性 / 承認者は誰か（Q1） | **運用ルール** | — |

> **「方向ゲート制」はポリシー（運用ルール）であり、その執行が機械か人かは属性の性質で決まる。**
> 順序のある属性はシステムが自動でゲートを回せる。順序のない本文等は、システムは diff を検出して人へ回すだけ。

---

## ディレクトリ構成（案）

```
criteria/                 # 評価基準（ルールの素性 + 観点本文）
  org/                    # 全社デフォルト
    code.md
    minutes.md
    spec.md
  teams/<team>/code.md       # チーム固有（org を継承・上書き）
  teams/<team>/code.react.md # 同 doc_type は複数可。union で結合（観点の additive 追加）
  projects/<proj>/code.md    # プロジェクト固有（team を継承・上書き）
policy/                   # 自動化ポリシー（マトリクス → 適用モード）
  org.yaml
  teams/<team>.yaml
  projects/<proj>.yaml
```

適用基準 = `文書タイプ × スコープ`。同じ `doc_type` のファイルを `org → team → project` の順に重ね、`id` 単位でマージする。

---

## 基準ファイルのスキーマ

### フロントマター（機械可読・ルーティング層）

```yaml
doc_type: code            # 文書タイプ。ファイルの対象（code | spec | minutes | ...）
scope: org                # org | team:<name> | project:<name>
extends: null             # 継承元。org は null。team は "org"、project は "team:<name>"
version: 1                # スキーマ/内容のバージョン
rules:
  - id: naming-convention      # 必須・一意。指摘の紐付け / 継承 / ポリシーの結合キー
    title: 命名規則            # 人間向け短いラベル
    category: readability      # 集計・フィルタ用の分類
    severity: error            # error | warning | info（ルール固有の素性）
    determinism: deterministic # deterministic | tradeoff | judgment（後述）
    enabled: true              # 適用範囲フラグ（継承時の disable に使う）
    override: loosen-needs-approval # 下位スコープからの上書き可否（後述）
```

> 対応モード（auto-fix / suggest / human-only）は **ここに書かない。**
> それはポリシー側で `determinism × severity` から写像する（責務分離）。

#### `determinism` の3値（基準を書く人が宣言する）

| 値 | 意味 | 例 |
|---|---|---|
| `deterministic` | 答えが一意。機械的に直せる | 命名規則違反・誤字・フォーマット |
| `tradeoff` | 直し方に幅はあるが定石が明確 | 冗長表現の整理・軽微なリファクタ |
| `judgment` | 意思決定が絡む。人間判断が要る | 要件矛盾・設計の是非・機密の扱い |

`02` の「AI に毎回判断させると揺れる」を避けるため、**基準を書く時点で人間が宣言**する（dashboard Q2 の運用案）。

### 本文（観点＝人間 & LLM 共用）

各ルールを `## <id> — <title>` 見出しで1セクション書く。プログラムは `id` で本文を抽出し、そのまま LLM プロンプトへ注入する。

```markdown
## naming-convention — 命名規則

変数・関数・クラスの命名が規約に沿っているかを評価する。

**チェック観点**
- 省略しすぎていないか / 役割が名前から分かるか

**良い例**
\`\`\`python
user_count = 0
\`\`\`

**悪い例**
\`\`\`python
uc = 0
\`\`\`
```

---

## 継承・オーバーライドの仕様

`org → team → project` の順にマージ。結合キーは `id`。

| 下位ファイルの記述 | 効果 |
|---|---|
| 上位に無い `id` | **追加**（別観点・言語別の例を足したいときもこれ＝別ファイルで union） |
| 上位と同じ `id`（メタのフィールド指定） | **上書き**（指定フィールドのみ） |
| 上位と同じ `id` で本文セクションあり | **本文の差し替え**（下記「本文の扱い」参照） |
| 同じ `id` で `enabled: false` | **無効化**（このスコープでは適用しない） |

例：「うちのチームは命名規則を warning に緩める」なら team ファイルに
`{ id: naming-convention, severity: warning }` だけ書く。
ただし**この「緩める」上書きには下記のガバナンスがかかる**。

### スコープ内マージ（同 `doc_type×scope` の兄弟ファイル）

上の表は**スコープ間**（org→team→project）の話で、これは意図的な上書きなので順序（下位が勝つ）が効く。
一方、同じスコープ内に複数ファイルを置けるようにしたため（`teams/frontend/code.md` ＋ `code.react.md`、Q10）、
**スコープ内のファイルは対等な兄弟**として扱う。ここには上書きの順序を**設けない**。各ルールには
**provenance（由来ファイルパス）** を必ず保持し、衝突時はそれを使って報告する。

兄弟ファイルが同じ `id` を持ったときの判定（レビュー実行前に1回、結果はキャッシュ）：

| 衝突の種類 | 判定方法 | 結果 |
|---|---|---|
| メタ（severity 等）が**同値** | 機械（決定的） | 無害 → そのまま共存 |
| メタが**異なる値** | 機械（決定的） | 矛盾 → **親スコープへフォールバック＋警告** |
| **本文**どうし | **LLM が「矛盾しているか」だけ判定** | 矛盾なし → 共存（両方の本文を当該 id の指針として union）／ 矛盾あり → **親へフォールバック＋警告** |

> ここでの LLM の役割は「厳しく/緩めの方向判定」ではなく **整合性（矛盾の有無）判定**。方向は順序がなく機械にも
> LLM にも安定して判定できないが、**矛盾の有無はより扱える**（→ 2軸の原則を壊さない）。判定後の「矛盾→フォールバック」
> という処理自体は決定的。注意：LLM 判定は確率的で、「矛盾なし」の誤判定（＝静かに不整合が共存）が最悪側なので、
> フォールバック時の警告は必ず人へ出す（Q9 と接続）。

### 本文（観点）の扱い

本文はプロースで**順序がない＝機械が「厳しく/緩め」を判定できない**（→ 2軸の「運用ルール」側）。
だから本文には小細工（追記/差し替えの自動安全判定）を持ち込まず、こう割り切る：

- **本文を与えない** → 親をそのまま継承（最頻ケース）。
- **本文を与える＝差し替え**。システムは「親と差分がある」事実(diff)だけ検出し、
  `open` 以外なら**承認フローへ回す**（人が厳しく/緩め/妥当を判断）。`locked` の本文差分は**機械的に拒否**。
- **観点や言語別の例を足したいだけ** → 本文を編集せず **別ファイルを足す**（additive に union）。
  本文差し替えの重い承認経路を踏まずに済む。

> ⚠️ **未決（dashboard Q9）**：差分を**いつ・何を**承認者へ打ち上げるかは別途設計する。
> 「diff を検出したら毎回通知」では運用が破綻する。バッチ単位・しきい値・dedup・
> ノイズ抑制（`open` や同一差分の再通知抑止）を含めて条件を決めること。

---

## 上書きガバナンス（方向ゲート制）

これは**運用ルール（ポリシー）**であり、その執行が機械か人かは属性の性質で決まる（→ 横断概念の2軸）。
「上書き可否」は一律では決めない。**方向（厳しく/緩め）× 対象（必須/推奨）** で扱いを変える。
原則：**安全側への上書きは自由、リスク側への上書きは承認 or 禁止。**

### 何が「リスク側（＝緩め）」か（順序のある属性＝システムが自動判定）

| 層 | 安全側（自由に上書き可） | リスク側（承認 or 禁止） |
|---|---|---|
| 基準 | ルール追加 / severity を上げる | severity を下げる / `enabled: false` / ルール削除 |
| ポリシー | 自動化を減らす（承認を増やす方向） | 自動化を増やす（`human_only`→`auto_fix_suggest`→`auto_fix_log_only`） |

本文・`determinism` は順序がないので、上表の自動判定には乗らない（人が見る）。本文は「本文の扱い」、
`determinism` は下記の注を参照。

> **方向は「直近の親（合成済みの実効値）」を基準に測る**（3段継承で重要）。
> 例：org=error → team=warning → project=error の naming-convention で、project の変更は
> team(warning) 基準で「厳しく」＝安全側。org の元値と同じかどうかは見ない。
> つまり**親が承認を得て緩めたものを、子が締め直すのは自由**（締め直しは常に安全側）。

> `determinism` は「事実」であり好みで書き換えない（Q6 原則）。事実の訂正が要るなら
> 全社基準への修正提案として扱う。チームが運用都合で触る対象ではない。

### `override` 属性の3値（全社基準が各ルールに宣言）

| 値 | 意味 |
|---|---|
| `locked` | 上書き不可（基準もポリシーも）。セキュリティ・コンプラ等の必須ライン |
| `loosen-needs-approval` | **既定**。厳しくは自由 / 緩めは管理者承認（PR）が必要 |
| `open` | 厳しくも緩めも自由（現場裁量に完全委任する推奨ルール） |

### 承認フローとの接続

リスク側の上書きは PR 化し、管理者が承認して初めて有効になる（dashboard **Q1** / `04` フィードバックループ）。
流し読みの「対象外」フラグも、緩める方向の提案ならこの承認ゲートを通る。

---

## 自動化ポリシーファイル

基準とは別ファイル。`determinism × severity` のマトリクスを適用モードへ写像する。
基準と同じく `org → team → project` で上書き可能。

```yaml
scope: org
extends: null
# determinism × severity → 適用モード
matrix:
  deterministic: { "*": auto_fix_log_only } # 一律ログのみ（🤖）
  tradeoff:      { "*": auto_fix_suggest }   # diff 提示・承認任意（✋）
  judgment:      { "*": human_only }         # AI は原案まで（💬）
# 個別ルールの例外（任意）
overrides:
  - rule: secret-in-code
    mode: human_only
```

### 適用モードと提示3区分（`02`）の対応

| 適用モード | 提示区分 | 振る舞い |
|---|---|---|
| `auto_fix_log_only` | 🤖 自動修正済み | 承認不要で適用・サマリに記録・一括 revert 可 |
| `auto_fix_suggest` | ✋ 要承認 | diff 提示・人間が適用ボタン |
| `human_only` | 💬 要判断 | AI が原案提示・人間が決定 |

---

## サンプル

- [examples/code.org.md](examples/code.org.md) … コード評価・全社デフォルト
- [examples/minutes.org.md](examples/minutes.org.md) … 議事録評価・全社デフォルト
- [examples/policy.org.yaml](examples/policy.org.yaml) … 全社デフォルトの自動化ポリシー
- [examples/code.team-frontend.md](examples/code.team-frontend.md) … frontend チーム差分（org を継承・上書き）
- [examples/code.team-frontend.react.md](examples/code.team-frontend.react.md) … React 固有の観点を additive に union（本文差し替えなし）
- [examples/code.project-checkout.md](examples/code.project-checkout.md) … checkout プロジェクト差分（team:frontend を継承＝3段目）

### 継承の効き方（frontend チームでの合成結果）

`org` の5ルールに上記2ファイルを `id` 単位でマージした結果。**緩め方向は要承認**。

| id | 由来 | severity | 効果 | 承認 |
|---|---|---|---|---|
| naming-convention | org→team上書き | ~~error~~ → **warning** | 緩め（本文は org 継承） | ✅ 要（loosen-needs-approval） |
| dead-code | org→team上書き | ~~warning~~ → **error** | 厳しく（安全側） | 不要 |
| long-function | org のまま | warning | 継承 | — |
| missing-test | org→team上書き | — | **無効化**（緩め） | ✅ 要 |
| secret-in-code | org のまま | error | 緩め試行は `locked` で**機械拒否** | 不可 |
| no-inline-style | team 追加 | warning | 新規（安全側） | 不要 |
| react-component-naming | react ファイル追加 | warning | 新規（union） | 不要 |
| hooks-rules | react ファイル追加 | error | 新規（union） | 不要 |

> ポイント：org の `naming-convention` 本文には一切触れていない。React 固有の例は
> 新 id（`react-component-naming` 等）として足すだけなので、本文差し替えの承認経路を踏まない。

### 3段継承の合成結果（checkout プロジェクト）

上の team 合成結果に、さらに [code.project-checkout.md](examples/code.project-checkout.md) を重ねた最終形。
**方向は直近の親（team の実効値）を基準に判定**する点に注目。

| id | チェーン（severity / 状態） | project の効果 | 承認 |
|---|---|---|---|
| naming-convention | org:error → team:**warning** → project:**error** | team基準で厳しく＝安全側（親の緩めを締め直す） | 不要 |
| missing-test | org:warning(有効) → team:**無効** → project:**error(有効)** | team基準で有効化＋厳しく＝安全側 | 不要 |
| secret-in-code | org:error（locked）→ … → project | 全段で不可侵。error が貫通 | 不可 |
| dead-code / long-function 他 | team の実効値をそのまま継承 | project は触らず | — |
| money-no-float | project で新規追加 | 新規（安全側） | 不要 |

> 検証で確認できたこと：①方向ゲートは「org の元値」ではなく**直近の親**を基準にするので、
> 親が承認を得て緩めたものを子が締め直すのは常に自由。②`locked` は段数に関係なく貫通する。
> ③provenance は org/team/project の3起点になり、衝突報告・差分通知（Q9/Q10）で由来段を示せる必要がある。

## 書いてみて見えた論点（dashboard へ反映候補）

- **本文と例の言語・形式**：コード例は言語ごとに複数要るか？ 文書タイプで「良い例/悪い例」の形が変わる（議事録は文章例）。
- **`category` の語彙**：自由記述だと集計がブレる。enum 化するか。
- **`enabled: false` 以外の disable 表現**：ポリシー override で実質無効化もできるため、無効化の責務が基準/ポリシーに二重化しないか整理が要る。
- **指摘と id の紐付け精度**：LLM が誤った id を付けた場合のフォールバック（未分類バケツ）が要る。
- ~~**同一 `doc_type×scope` の複数ファイル許容**（継承サンプルで発覚）~~ → 方針合意（Q10）。
  スコープ内は対等な兄弟・順序なし。provenance を保持し、同 id 衝突はメタ＝決定的・本文＝LLM 矛盾判定で
  「共存 or 親フォールバック＋警告」。詳細は[スコープ内マージ](#スコープ内マージ同-doc_typescope-の兄弟ファイル)。
- **`override`（特に `locked`）を宣言できるのは誰か**（3段継承サンプルで発覚, Q11）：現仕様は「locked は org が宣言」。
  だが team/project は**自分が追加した新ルール**には `override` を付けている（例 `money-no-float`）。
  「継承ルールの override は宣言元(org)のみ変更可・locked は段に関係なく不可侵／新規ルールには自スコープで
  open・loosen は宣言可、locked は org 限定？」あたりの線引きを決める。
