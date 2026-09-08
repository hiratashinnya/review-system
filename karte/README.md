# karte

是正ループの診断カルテ（`tmp/_karte/issue-<N>.md`）を操作する CLI。`python3 -m karte <verb>`。

verb の一覧・追記規律・改ざん防止の仕組みは `karte/cli.py` と `karte/model.py` のモジュール
docstring を正本とする。本 README は `close-attempt` の**既定値の解決規則**（Issue #378 AC
「既定値の解決規則が `--help` および README から読み取れるようにする」）と、
**`scope` / `disposition` と verdict のゲート**（Issue #495）、**`check` の判定規則と
`deferred`/`waived` の除外の集約**（Issue #503）、**`change_kind` の語彙**（同 観測2）を
掃引的に説明する。

## `scope` / `disposition` と `status` の verdict（Issue #495）

### なぜ入れたか

「スコープ外事項」と分類された指摘は、以前は finding の列に入らなかった。その結果
**実害判定（`harm`）・カルテ記録・`status` の verdict のすべてを一度に迂回**でき、実害ありの
指摘が未処置のまま `clean` を通過して merge された（PR #490。merge 後に実害ありと確定し
Issue #493 として流出）。迂回に必要なのは「スコープ外」と書くことだけで、特別な権限も操作も
要らなかった。そこで **`## Findings` をスコープの内外を問わない単一の列**にし、
「スコープ外」というラベルが実害判定の免除として機能しないようにした。

### `scope`（必須・免除力なし）

- 値は `in`（当該 PR のスコープ内）／`out`（スコープ外）。
- **`ingest-review` では必須**。欠落は取り込みごと拒否する（`harm` 欄欠落と同じ扱い）。
  任意キーにすると書かれないため。
- **レビューアの申告であって確定ではない**。主文脈・オーナーが覆せる。
- **`scope: out` は実害判定・記録・verdict のいずれの免除にもならない。** スコープの内外は
  「誰がいつ直すか」の話であって「実害があるか」の話ではない（判定軸を混ぜない）。
- **移行措置**：`scope` を持たない**既存カルテ**は `in` として読む（`tmp/` は版管理外だが、
  進行中の Issue の台帳が読めなくなると是正ループが止まるため）。緩和は**台帳の読み取りだけ**で、
  新規の `ingest-review` は必須のまま。値が不正（`scope: outside` 等）なら台帳側でも拒否する
  ——「無い」（既定へ倒してよい）と「値が不正」（倒すと意味が変わる）は別物。

### `disposition`（`harm: real` に対するオーナー判断の記録）

下表の「verdict への影響」は **`harm: real` の finding についての話**である（次項参照）。

| 値 | 意味 | 必須の付随キー | verdict への影響（`harm: real`） |
|---|---|---|---|
| （未記載） | 未決定 | — | **`clean` を妨げる** |
| `fix-here` | 当該 PR で直す | — | 直って `status: resolved` になるまで `clean` を妨げる |
| `deferred` | 別 Issue へ申し送る | `deferred_to` | 妨げない（`status` は `open` のまま） |
| `waived` | オーナーが明示的に処置不要を許可 | `waived_by` / `waived_reason` | 妨げない（`status` は `open` のまま） |

- `deferred_to` は `#123` / `123` / Issue の URL のいずれかで書く。散文（「別 Issue で対応」）は
  行き先を解決できないため拒否する。
- `waived` に許可者と理由を要求するのは、`.claude/rules/03-operational.md`
  「『対応不要』を AI が独断で書かない」に対する **記録の強制**（許可者と理由を書かずに
  `waived` を通せなくする）。**オーナー判断そのものの機械強制ではない**——下記「既知の限界」。
- 宣言した `disposition` に属さない付随キー（例：`deferred` なのに `waived_by`）は拒否する。
  取り違えて古い方針を現行の方針と誤読するのを防ぐため。
- 値は毎ラウンドのレポートで上書きされる。**書き忘れると未決定へ倒れて `clean` を妨げる**
  （fail-close 側）。だれがそれを書くか（＝毎ラウンドの再掲を誰が担うか）は
  `.ai/skills/issue-pipeline/SKILL.md` ②-c を正本とする（**主文脈**が、オーナーの決定を
  次ラウンドの取り込みレポートへ書き足してから `ingest-review` する。レビュー担当は
  `disposition` を書かない契約）。

### `clean` の解除力は `harm: real` にだけ与える（オーナー確定・2026-09-07）

`harm: none` の finding に `disposition: deferred` / `waived` を書いても **verdict は動かない**
（記録としては残る）。`harm: none` の未解消がある間は verdict が `no-harm-only` のままになり、
「未解消がすべて実害なしになったらオーナーへ打ち上げる」STOP
（`.ai/skills/issue-pipeline/SKILL.md`「実害の定義とエスカレーション」）が生きる。

理由：`disposition` はそもそも「`harm: real` に対するオーナー判断の記録」として導入した
（Issue #495 の提案挙動 3〜5 はいずれも `harm: real` が主語）。解除力を `harm` の値によらず
与えると、実害なしの指摘に `deferred` と適当な Issue 番号を 2 行書くだけで verdict が
`clean` へ変わり、**AI が単独で既存のオーナー STOP を消せる**。それは本 Issue が塞いだ
「ラベルを書くだけで clean を通す」経路と同型のものを `harm: none` 側へ新設することになる。

### 既知の限界（多層防御の一枚であって sandbox ではない）

- `waived_by` / `waived_reason` は自由記述のスカラであり、**書いた主体がオーナー本人かを
  機械側は区別しない**。`ingest-review` を実行するのは主文脈（AI）であり、
  `.claude/hooks/agent-command-gate.sh` の `KARTE_ALLOWED_SUBCOMMANDS` が締め出しているのは
  是正当事者ロール（`issue-fixer` 等）だけである。
- `deferred_to` は形式（`#123` / `123` / URL）だけを検査し、**指す Issue が実在するかは
  検証しない**。
- したがってここで強制しているのは **記録**であって**オーナー判断**ではない。カルテの改ざん
  防止（`karte/model.py` の「改ざん防止の機械的裏付けと既知の限界」）と同じく、静的検査で
  閉じきれない面はプロンプト規律・レビュー分離・GitHub 側の保護と併用して塞ぐ（Issue #129）。

### verdict の定義

`clean` は「未解消 finding が 0 件」ではなく **「`clean` を妨げる未解消 finding が 0 件」**。

- `blocking_findings`（`status --json`）＝未解消の finding のうち、**`harm: real` かつ
  `disposition` が `deferred`/`waived`** のものを除いた残り。これが空のときだけ `clean`。
- そのうち `harm: real` があれば `harmful-open`、無ければ `no-harm-only`。
- `blocking_harmful`＝**`clean` を妨げる実害あり**（`blocking_findings` ∩ `harmful_open`）。
  `harmful-open` の verdict を成立させている当の集合。
- `undecided_disposition`＝`harm: real` かつ `disposition` 未決定のまま未解消の finding。
  **`scope: out` でも免除されない**。
- **`no-harm-only` は「台帳の未解消が全件実害なし」ではない**。意味は「**`clean` を妨げる**
  未解消がすべて実害なし」であり、申し送り（`deferred`）／処置不要（`waived`）と決めた
  `harm: real` の finding は `status: open` のまま別に残りうる。`harmful_open`（`--json`）と
  `status` の「実害あり」行は**台帳上の未解消全件**の内訳なので、そこには残った `harm: real`
  も出る（verdict と食い違って見えるのはこのため）。

#### `harm: real` の 3 集合の包含関係（PR #496 F-495-06）

`undecided_disposition` ⊆ `blocking_harmful` ⊆ `harmful_open`。

| キー | 含むもの | 用途 |
|---|---|---|
| `harmful_open` | 未解消かつ `harm: real` の**全件**（`deferred`/`waived` を含む） | 台帳上の実害ありの内訳 |
| `blocking_harmful` | そのうち `clean` を妨げるもの（＝`disposition` が未決定か `fix-here`） | **verdict `harmful-open` の説明** |
| `undecided_disposition` | さらにそのうち `disposition` が未決定のもの | オーナー判断がまだ要るもの |

`blocking_harmful` と `undecided_disposition` の差は `fix-here`（当該 PR で直すと決めたが
まだ直っていない）の分。`undecided_disposition` が空でも `fix-here` が残れば `harmful-open`
のままなので、**verdict の説明に `undecided_disposition` を使わない**。

消費者に `blocking_findings` と `harmful_open` の積を取らせず `blocking_harmful` を直接返すのは、
積の取り方を各消費者に委ねると F-495-05 と同型の誤読（verdict と内訳の意味の取り違え）が
消費者側で再発するため。

**`status` の本文出力（非 `--json`）も同じ 3 集合を包含関係の順に行として出す**
（`clean を妨げる未解消` → `clean を妨げる実害あり` → `実害あり・disposition 未決定`）。
機械向けにだけ積を出して人間の読み手には積を取らせる、という非対称を残さないため
（PR #496 F-495-07）。「実害あり（未解消・申し送り/処置不要と決めたものを含む）」行は
これらとは別の軸（`harmful_open`＝台帳上の未解消全件の内訳）なので、包含関係の 3 行とは
分けて読む。

### `deferred` を `resolved` にしない（二層にする理由）

`status: resolved` は「当該 PR で実際に直った」だけに限定する。`deferred` を `resolved` に
倒すと「**別 Issue へ移したと書くだけで指摘が台帳から消える**」経路ができ、本 Issue が塞ごうと
している穴が形を変えて再発する。よって `deferred`/`waived` は `status: open` のまま残し、
**verdict の上でだけ** `clean` を妨げなくする。

### `deferred`/`waived` の除外は 1 箇所に置く（Issue #503）

**「当該 PR では処置しない」と決まった finding を判定から外す規則は、
`karte/model.py` の `Finding.needs_remediation`（＝`Finding.cleared_by_disposition` を
経由する述語）1 箇所にだけ実装する。** 次の 3 経路はこの単一の述語を共有する。

| 判定経路 | 何に使うか | 集合の入口 |
|---|---|---|
| `status` の verdict | `clean` を妨げる未解消 finding | `Karte.remediation_findings()`（`--json` の `blocking_findings`） |
| `check` の診断網羅要求 | 当該ラウンドで Attempt（診断）が要る finding | 同上を当該ラウンドで絞る |
| 無進捗検知（`escalate`） | 「3 ラウンド連続未解消」を数える対象 | 同上（`karte/cli.py` の `_stalled_ids`） |

`render` の `★無進捗` の印も `_stalled_ids` から引く（`status` は無進捗と言わないのに
`render` だけが是正担当へ印を見せる、という食い違いを作らないため）。

**なぜ集約するか。** Issue #495 の実装は除外を verdict 算出にだけ入れ、他の経路へ反映しなかった。
その結果、同じ取りこぼしが**経路の数だけ別々に**開いた——

- `check` が `deferred` の finding にも診断を要求し、是正担当が指示どおりそれを触らずに他を
  完璧に是正しても必ず `EXIT_ERROR` を返した（Issue #503 観測1）。停止ゲートが**毎ラウンド
  1 回 block する**ようになると、本物の未診断（是正担当が診断を怠ったケース）を検出できなくなる。
- 無進捗検知が「誰も直さないと決めた finding」を拾い、`escalate: yes` を偽陽性で出した（同 観測3）。
  `deferred` を 1 件でも抱えたまま 3 ラウンド以上回る PR は毎回これを出すため、本物の無進捗が
  偽陽性に紛れて見落とされる。

いずれも「常に鳴るゲートは本物を検出できなくなる」という同じ形の形骸化である。今後
`deferred`/`waived` を参照する判定を足すときは、この述語を経由させれば自動的に同じ規則が効く。

### `check` の判定規則（Issue #503）

```
python3 -m karte check [--issue <N>] [--round <R>]
```

`check` は SubagentStop フック（`.claude/hooks/subagent-stop-gate.sh`）が `issue-fixer` の
停止可否を判定するために使う。**合格（`EXIT_OK`）の条件は次の 2 つを同時に満たすこと。**

1. **当該ラウンドの Attempt が、診断が要る未解消 finding を網羅している。**
   - 対象は「当該ラウンドで挙げられた（`rounds` に `R` を含む）」かつ
     「`Finding.needs_remediation` が真」の finding。
   - **`disposition` が `deferred` / `waived` の finding は対象から外れる**（上表の集約）。
     診断を求めるべきなのは「これから直す finding」であって「直さないと決まった finding」
     ではない。後者に診断を書かせることは、`.claude/rules/03-operational.md`
     「スコープ拡大禁止」に反する記録を台帳へ入れさせることでもある。
   - 除外した finding は黙って落とさず、`診断不要（disposition で …）` 行として出力に出す。
   - 当該ラウンドの Attempt が 1 件も無ければ `EXIT_ERROR`。
2. **カルテ上の全 Attempt が `close-attempt` 済み**（`### Result k` を持つ）。
   当該ラウンド以前だけでなく、**先のラウンドを名乗った Attempt も含めて全件**
   （`append --round <大きい値>` を逃げ道にしない）。

`status` の verdict と `check` は `disposition` について**同じ規則**で動く
（片方だけが `deferred` を要求する状態＝同じ台帳から機械が 2 つの異なる結論を出す状態を作らない）。
ただし両者が答える問いは別である——`check` は「**このラウンドの是正が診断を伴っていたか**」、
`status` は「**この PR を clean と呼べるか**」。したがって `check` が `EXIT_OK` でも
`disposition: fix-here` の未修正が残っていれば `status` は `harmful-open` のままになる。

**互換性**：判定規則の変更のみでカルテのフォーマットは不変。ただし**これまで `EXIT_ERROR` に
なっていたラウンドが `EXIT_OK` になる**ため、`check` の終了コードに依存する CI・フックの
挙動は変わる（＝`deferred` を含むラウンドで毎回 1 回鳴っていた block が鳴らなくなる）。

### `change_kind` の語彙（Issue #503 観測2）

`append --change-kind` に指定できる値。類似判定の**宣言信号**（`root_cause` 一致に加えて
`change_kind` 一致か `targets` 交差を見る）の入力であり、飽和検知の材料になる。

| 値 | 意味 |
|---|---|
| `logic` | 処理・分岐・アルゴリズムの変更 |
| `data-structure` | 型・データ表現・スキーマの変更 |
| `interface` | 関数シグネチャ・CLI 面・公開 API の変更 |
| `config` | 設定値・設定ファイル・閾値の変更 |
| `test` | テストの追加・修正 |
| `doc` | **文書だけの変更**（README・`docs/**`・エージェント定義本文・docstring。コードの挙動を変えない） |
| `revert` | 前の変更の取り消し |

- `doc` は Issue #503 観測2 で追加した。追加前は文書のみの是正ラウンドで実態に合う値が無く、
  是正担当が已むなく `config` を選んだ（Issue #493 の是正ラウンド2 で実測）。実態と違う値が
  入ると (a) 後から読む者が「設定を変えた是正」と誤読し、(b) 飽和判定が**別の `config` 変更との
  距離を実態より近く**算出する。是正ラウンドの相当数は文書のみの変更であり、再発頻度は低くない。
- **既存カルテの `config` 記録は遡って読み替えない。** 移行スクリプトも読み替えマップも持たない。
  理由は 2 つ——(1) 台帳は追記のみ（既に書かれた Attempt ブロックはどの verb も書き換えない）で
  あり、遡って書き換えると改ざん防止の前提である append-only の不変条件を自ら破ることになる。
  (2)「当時どう申告したか」は飽和判定が実際に使った入力であり、後から書き換えると過去ラウンドの
  判定結果を再現できなくなる（監査可能性の喪失）。
- **飽和判定への影響**は「新しい `doc` の Attempt が、過去の `config` の Attempt と
  `change_kind` 経由では類似と判定されなくなる」ことに限られる。`root_cause` 一致＋`targets`
  交差の経路と、実測 touched-set 一致の経路（ラベルを付け替えても効く実測信号）は従来どおり働く。
  すなわち語彙追加は飽和判定を**緩める方向**に働きうるが、それは「実態が違う変更を同種と数えて
  いた」過大計上の解消であって、検知力の意図的な低下ではない。

### ハンドオフの `out_of_scope_findings`

`issue-implementer` / `issue-fixer` がハンドオフに書く `out_of_scope_findings` も、finding と
同じキー（`harm`/`harm_detail`/`severity`/`scope: out`/`locus`/`summary`/`evidence`/
`expected`/`recheck`）を揃える。主文脈がそれを finding ブロックへ写して `ingest-review` する
（`pr-reviewer` だけ直しても半分しか塞がらない）。**取り込みの実行は主文脈**で、是正当事者には
`ingest-review` を許さない（`.claude/hooks/agent-command-gate.sh` の
`KARTE_ALLOWED_SUBCOMMANDS`）。

## `close-attempt` の既定値解決規則

```
python3 -m karte close-attempt --issue <N> --outcome <fixed|partial|no-change|regressed> \
    [--attempt <k>] [--base <ref>] [--diff-file <path>] [--finding-ids ...] [--note <text>]
```

### `--attempt`（対象 Attempt 番号・Issue #378）

- **省略時**：カルテ上で**未クローズ**（`### Result k` を持たない）Attempt を数える。
  - **ちょうど1つ**なら、それを対象にする（最新でなくてもよい）。「1つ append → すぐ close」
    という一般的な運用ではこれで従来どおり動く。
  - **2つ以上**あれば、どれに記録するつもりか読み取れないため **fail-close**（`EXIT_ERROR`）
    し、未クローズの Attempt 番号を列挙したうえで `--attempt` の明示を要求する。
  - **0個**なら fail-close し、`--attempt` の明示または先に `append` することを促す。
    「0個」は2通りの状態を含みうるため、`--help`・実際のエラーメッセージはそれぞれを
    区別して述べる（F-378-03）——
    - **Attempt が1件も無い**（`append` をまだ1度も呼んでいない）。
    - **Attempt はあるが全件クローズ済み**（結果は既に記録されている）。
- **明示時**：その番号をそのまま使う（既存 Attempt の存在・未クローズであることは
  引き続き検証する）。

複数の Attempt を先に `append` してからまとめて `close-attempt` する運用では、必ず
`--attempt` を明示すること。省略した状態で複数未クローズが残っていると、狙った Attempt
とは違う Attempt へ記録が吸い込まれる事故が過去に2ラウンド連続で発生した（PR #364
是正ラウンド2・3）。

### `--base` / `--diff-file`（実測 touched-set の算出元・Issue #355）

- `--diff-file` を指定すると、そのファイルの内容を unified diff として touched-set を
  算出する（git を呼ばない）。
- 省略時は `git diff --unified=0 --no-color <--base>` を実行する。`--base` の既定は
  `HEAD`。
- **注意（footgun）**：commit・push を済ませたあとに既定 `--base HEAD` で
  `close-attempt` を実行すると、作業ツリーが HEAD と一致しているため diff が**空**に
  なる。この場合は変更前の commit（例：直前の commit 1つだけの場合は `HEAD~1`）を
  `--base` に明示するか、commit 前に取得した diff を `--diff-file` で渡すこと。
- **空 diff は fail-close する**：実測 touched-set が空のまま `--outcome` が
  `fixed` / `partial` / `regressed` だと、無言で `touched: []` が append-only の台帳に
  固定されてしまう（訂正不可）。これを防ぐため、touched-set が空のときは
  `--outcome no-change`（差分なしで解消と判定される finding。例：ドキュメントの解釈違い
  で実装は元々正しかった等）である場合を**除き** fail-close する。

### 宣言 targets と実測 touched の不一致検知（保険的チェック・Issue #378 C）

`close-attempt` は、Attempt の宣言 `targets`（ファイルレベル）と実測 `touched`
（ファイルレベル）が**一切重ならない**場合、警告を stdout に出す（拒否はしない）。
`--attempt` を誤って別の Attempt に向けてしまった場合の事後検知として働く。ただし
touched-set 自体が空（`--base` を誤って空 diff になったケース）は検知できない——
そちらは上記の空 diff fail-close が別途担う。

## 終了コード

`dsv2` に合わせる：`0` OK ／ `2` 未検出 ／ `3` 類似飽和（`append` 拒否）／
`4` 前提違反・検証失敗（fail-close）。
