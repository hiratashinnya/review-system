# karte

是正ループの診断カルテ（`tmp/_karte/issue-<N>.md`）を操作する CLI。`python3 -m karte <verb>`。

verb の一覧・追記規律・改ざん防止の仕組みは `karte/cli.py` と `karte/model.py` のモジュール
docstring を正本とする。本 README は `close-attempt` の**既定値の解決規則**（Issue #378 AC
「既定値の解決規則が `--help` および README から読み取れるようにする」）を掃引的に説明する。

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
  - **0個**（全 Attempt クローズ済み）なら fail-close し、`--attempt` の明示または
    先に `append` することを促す。
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
