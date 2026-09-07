# karte

是正ループの診断カルテ（`tmp/_karte/issue-<N>.md`）を操作する CLI。`python3 -m karte <verb>`。

verb の一覧・追記規律・改ざん防止の仕組みは `karte/cli.py` と `karte/model.py` のモジュール
docstring を正本とする。本 README は `close-attempt` の**既定値の解決規則**（Issue #378 AC
「既定値の解決規則が `--help` および README から読み取れるようにする」）と、
**`scope` / `disposition` と verdict のゲート**（Issue #495）を掃引的に説明する。

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
- `undecided_disposition`＝`harm: real` かつ `disposition` 未決定のまま未解消の finding。
  **`scope: out` でも免除されない**。
- **`no-harm-only` は「台帳の未解消が全件実害なし」ではない**。意味は「**`clean` を妨げる**
  未解消がすべて実害なし」であり、申し送り（`deferred`）／処置不要（`waived`）と決めた
  `harm: real` の finding は `status: open` のまま別に残りうる。`harmful_open`（`--json`）と
  `status` の「実害あり」行は**台帳上の未解消全件**の内訳なので、そこには残った `harm: real`
  も出る（verdict と食い違って見えるのはこのため。`clean` を妨げる実害ありだけを見たいときは
  `blocking_findings` と `harmful_open` の積、または `undecided_disposition` を使う）。

### `deferred` を `resolved` にしない（二層にする理由）

`status: resolved` は「当該 PR で実際に直った」だけに限定する。`deferred` を `resolved` に
倒すと「**別 Issue へ移したと書くだけで指摘が台帳から消える**」経路ができ、本 Issue が塞ごうと
している穴が形を変えて再発する。よって `deferred`/`waived` は `status: open` のまま残し、
**verdict の上でだけ** `clean` を妨げなくする。

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
