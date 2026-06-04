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
| `override`（locked/tighten-only/open） | 機械判定 | 方向 × `override` で allow/reject を自動判定（承認ステップ無し） |
| **本文（観点プロース）** | **運用ルール** | 「親と差分がある」事実(diff)のみ。**厳しく/緩めは判定不能** |
| `determinism` | **運用ルール** | 変更が緩めかではなく「事実として正しいか」が問題 |
| どのルールを `open`/`locked` にするか・誰が基準を編集してよいか（Q1） | **運用ルール** | — |

> **方向ゲートの allow/reject 自体は決定的な機構（設計）。** 順序のある属性はシステムが自動でゲートを回せる。
> 運用ルールなのは「org がどのルールに緩めを許す(`open`)か」「誰が基準を編集してよいか」の方。本文等の順序なし属性は diff を検出して人へ回す。

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
    category: readability      # 集計・フィルタ用のゆるいタグ（自由記述・推奨語彙は後述）
    severity: error            # error | warning | info（ルール固有の素性）
    determinism: deterministic # deterministic | tradeoff | judgment（後述）
    enabled: true              # 適用範囲フラグ（継承時の disable に使う）
    override: tighten-only     # locked | tighten-only(既定) | open。下位の上書き可否（後述）
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

`org → team → project` の順にマージ（結合キー `id`）。これは「**より具体的な文脈が勝つ**」という継承の機構。
**org の権威は別レイヤ（`override`）が守る**：下位は org の下限を壊さない範囲でだけ調整する（→ [上書きガバナンス](#上書きガバナンス方向ゲート制)）。

| 下位ファイルの記述 | 効果 | 可否 |
|---|---|---|
| 上位に無い `id`（新規ルール） | **追加**（別観点・言語別の例も別ファイルで union） | 常に可 |
| 上位と同じ `id` を**厳しく**（severity を上げる等） | **上書き**（指定フィールドのみ） | 常に可（下限を上げる） |
| 上位と同じ `id` に**本文**を与える | **本文の差し替え**（下記「本文の扱い」） | 別途扱い |
| 上位と同じ `id` を**緩め / `enabled: false`** | 緩め・無効化 | **既定で機械拒否**（`open` のルールのみ可） |
| `locked` のルール | — | 触れない |

例（安全側）：「決済チームは命名規則を error に**厳しく**する」→ team に `{ id: naming-convention, severity: error }`。常に可。
例（緩め）：org が `naming-convention` を `override: open` にしている場合に限り team は warning に緩められる。`open` でなければ機械拒否。

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
- **本文を与える＝差し替え**＝org の観点を下位が書き換えること。本文は順序がなく「厳しく/緩め」が判定できない以上、
  org 権威で**既定は機械拒否**。差し替えてよいのは org が `open` にしたルールだけ（`locked` はもちろん拒否）。
- **観点や言語別の例を足したいだけ** → 本文を編集せず **別ファイルを足す**（additive に union）。
  既存本文を触らないので機械拒否に当たらない。

> ⚠️ **未決（dashboard Q9）**：差分を**いつ・何を**承認者へ打ち上げるかは別途設計する。
> 「diff を検出したら毎回通知」では運用が破綻する。バッチ単位・しきい値・dedup・
> ノイズ抑制（`open` や同一差分の再通知抑止）を含めて条件を決めること。

---

## 上書きガバナンス（方向ゲート制）

**権威モデル：org が下限（floor）を敷き、下位スコープ（team/project）は下限を壊さない範囲でだけ specialize する。**
「下位が org を上書きする」のではなく、**org がルールごとに委譲する範囲の中で下位が調整する**（→ 横断概念の2軸の運用側）。

| 操作 | 既定の扱い |
|---|---|
| ルール**追加**（親に無い id） | **自由** |
| **厳しく**（severity を上げる等） | **自由**（org の下限を上げる＝意図を壊さない） |
| **緩め / `enabled: false`**（severity を下げる・無効化・削除） | **既定で機械拒否**。org が `open` 宣言したルールだけ可 |
| `locked` のルール | 一切触れない（厳しくも緩めも機械拒否） |

ポリシー（自動化）も同型：自動化を**減らす**（人を増やす）方向は自由、**増やす**方向は既定で不可・`open` のみ。

本文・`determinism` は順序がないので、この方向判定には乗らない（人が見る）。本文は「本文の扱い」、
`determinism` は下記の注を参照。

> **方向は「直近の親（合成済みの実効値）」基準で測る**（3段継承で重要）。
> 例：naming が `open` で org=error → team=warning（緩め・open だから可）→ project=error（team 基準で「厳しく」＝自由）。
> 締め直し（厳しく）は常に自由。org の元値ではなく直近の親と比べる。

> `determinism` は「事実」であり好みで書き換えない（Q6 原則）。事実の訂正が要るなら
> 全社基準への修正提案として扱う。チームが運用都合で触る対象ではない。

### `override` 属性の3値（全社基準が各ルールに宣言）

| 値 | 緩め・無効化 | 厳しく・追加 | 用途 |
|---|---|---|---|
| `locked` | ✕ | ✕ | 触れない。セキュリティ・コンプラ等の必須ライン |
| `tighten-only`（**既定**） | ✕（機械拒否） | ○ | **org 権威**。下位は締める/追加のみ。緩めたいルールは org が個別に `open` にする |
| `open` | ○ | ○ | 緩める裁量を org が明示委任した推奨ルール |

> 完全に機械判定（方向 × `override` → allow / reject）。**承認ステップは無い**。緩めたいなら org がそのルールを `open` にする（org の一手）。

### 基準変更の確認との接続

個々の上書きの可否は `override` で**機械的に**決まる（緩め＝reject か open、承認は挟まない）。
人間の確認が要るのは、**基準ファイルそのものを変える行為**——org がルールを `open` にする / 既定を変える / `locked` を足す等——のとき（dashboard **Q1** / `04` フィードバックループ）。

> **MVP 注**：上書きの allow/reject はアクター不要の機械判定で成立する。
> 「誰が基準ファイルを編集・確定してよいか」だけがアクターの話で、MVP は**区別しない**（単一ユーザー・人間確認まで）。
> ロール強制（RBAC）は将来。役割ラベル（管理者/レビュア/メンテナ）は当面**記述的**な呼称にすぎない。

### 警告の既出判定（warning ledger）

設定の矛盾・ルール逸脱・スコープ内衝突などの**システム→人への警告**を毎回出すと、めんどくさがられて形骸化する。
そこで**既出は再警告しない**（Q9 のノイズ抑制の中核機構・完全に機械的）：

- 検知時に **`content_hash = hash(対象ルールのメタ ＋ 本文)`** を計算し、`{ rule_id, content_hash, first_seen }` を append-only の**警告レジャー**に記録。
- 検知のたびにレジャーを引く：
  - **未出**（同 `rule_id × content_hash` が無い）→ **警告を発する**＋記録。
  - **既出** → **警告しない**。レポートには「既知」として**混ぜるだけ**。
- 対象のメタ/本文が変われば hash が変わる＝**新しい逸脱として再警告**（正しい挙動）。

> なぜ警告には状態（レジャー）を持たせ、レビュー指摘（Q14）には持たせないか：
> **レビュー指摘**は文書に問題が残る限り毎回出すべき（再提出＝再レビュー、ステートレスでよい）。
> **設定への警告**は"一度示せば足りる人間の判断待ち"で、繰り返しはノイズ。**状態の要否がちょうど逆**。

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

`org` の5ルールに上記2ファイルを `id` 単位でマージした結果。**緩め・無効化は org が `open` したものだけ通る**。

| id | 由来 | severity | 効果 | 可否 |
|---|---|---|---|---|
| naming-convention | org(`open`)→team | ~~error~~ → **warning** | 緩め（本文は org 継承） | ✅ 可（`open` だから） |
| dead-code | org(`tighten-only`)→team | ~~warning~~ → **error** | 厳しく | ✅ 可（常に自由） |
| long-function | org のまま | warning | 継承 | — |
| missing-test | team が無効化を試行 | warning（維持） | `enabled:false` 試行 | **✕ 機械拒否**（`tighten-only`） |
| secret-in-code | team が緩めを試行 | error（維持） | 緩め試行 | **✕ 機械拒否**（`locked`） |
| no-inline-style | team 追加 | warning | 新規 | ✅ 可 |
| react-component-naming | react ファイル追加 | warning | 新規（union） | ✅ 可 |
| hooks-rules | react ファイル追加 | error | 新規（union） | ✅ 可 |

> ポイント：org の `naming-convention` 本文には一切触れていない。React 固有の例は
> 新 id（`react-component-naming` 等）として足すだけなので、本文差し替えの承認経路を踏まない。

### 3段継承の合成結果（checkout プロジェクト）

上の team 合成結果に、さらに [code.project-checkout.md](examples/code.project-checkout.md) を重ねた最終形。
**方向は直近の親（team の実効値）を基準に判定**する点に注目。

| id | チェーン（severity / 状態） | project の効果 | 可否 |
|---|---|---|---|
| naming-convention | org(`open`):error → team:**warning** → project:**error** | team基準で厳しく（親の緩めを締め直す） | ✅ 可（厳しくは自由） |
| missing-test | org:warning（team の無効化は拒否済）→ project:**error** | org 既定のまま warning→error に締める | ✅ 可（厳しくは自由） |
| secret-in-code | org:error（`locked`）→ … → project | 全段で不可侵。error が貫通 | 触れない |
| dead-code / long-function 他 | team の実効値をそのまま継承 | project は触らず | — |
| money-no-float | project で新規追加 | 新規 | ✅ 可 |

> 検証で確認できたこと：①方向は「org の元値」ではなく**直近の親**を基準にするので、締め直し（厳しく）は常に自由。
> ②緩め・無効化は org が `open` にしたルールだけ通る（team の missing-test 無効化は機械拒否）。
> ③`locked` は段数に関係なく貫通。④provenance は org/team/project の3起点になり、衝突報告・差分通知（Q9/Q10）で由来段を示せる必要がある。

## 書いてみて見えた論点（dashboard へ反映候補）

- **本文と例の言語・形式**：コード例は言語ごとに複数要るか？ 文書タイプで「良い例/悪い例」の形が変わる（議事録は文章例）。
- ~~**`category` の語彙**：enum 化するか~~ → 確定（Q8）。**enum 強制はしない**（基準ファイルはテキスト編集できるので非現実的）。
  自由記述＋**推奨語彙のソフト規約**で運用する。推奨：`readability` / `maintainability` / `security` / `quality` /
  `correctness` / `performance`（コード系）、`clarity` / `structure` / `completeness`（文章系）。
  集計は存在する文字列でグループ化。語彙の正規化（AI クラスタリング提案）は将来の育成機能候補で、MVP では作らない。
- **`enabled: false` 以外の disable 表現**：ポリシー override で実質無効化もできるため、無効化の責務が基準/ポリシーに二重化しないか整理が要る。
- **指摘と id の紐付け精度**：LLM が誤った id を付けた場合のフォールバック（未分類バケツ）が要る。
- ~~**同一 `doc_type×scope` の複数ファイル許容**（継承サンプルで発覚）~~ → 方針合意（Q10）。
  スコープ内は対等な兄弟・順序なし。provenance を保持し、同 id 衝突はメタ＝決定的・本文＝LLM 矛盾判定で
  「共存 or 親フォールバック＋警告」。詳細は[スコープ内マージ](#スコープ内マージ同-doc_typescope-の兄弟ファイル)。
- **`override`（特に `locked`）を宣言できるのは誰か**（3段継承サンプルで発覚, Q11）：現仕様は「locked は org が宣言」。
  だが team/project は**自分が追加した新ルール**には `override` を付けている（例 `money-no-float`）。
  「継承ルールの override は宣言元(org)のみ変更可・locked は段に関係なく不可侵／新規ルールには自スコープで
  open・loosen は宣言可、locked は org 限定？」あたりの線引きを決める。
