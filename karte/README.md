# karte

是正ループの診断カルテ（`tmp/_karte/issue-<N>.md`）を操作する CLI。`python3 -m karte <verb>`。

verb の一覧・追記規律・改ざん防止の仕組みは `karte/cli.py` と `karte/model.py` のモジュール
docstring を正本とする。本 README は `close-attempt` の**既定値の解決規則**（Issue #378 AC
「既定値の解決規則が `--help` および README から読み取れるようにする」）と、
**`scope` / `disposition` と verdict のゲート**（Issue #495）、**`check` の判定規則と
`deferred`/`waived` の除外の集約**（Issue #503）、**`change_kind` の語彙**（同 観測2）、
**`harm_detail` の内容 lint と allowlist**（Issue #511）を掃引的に説明する。

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
- **レビューアの申告であって確定ではない**。ただし**覆せるのはオーナーだけ**であり、`disposition` と
  同じくオーナー専権である。主文脈は覆しの判断主体ではなく、オーナーが決めた値を記録する
  担い手にすぎない（正本＝`.ai/skills/issue-pipeline/SKILL.md` ②-c。機械側がこれを
  検証していないことは下記「既知の限界」）。
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
- `decide` と非保護モードの `ingest-review` は、宣言した `disposition` に属さない付随キー
  （例：`deferred` なのに `waived_by`）を拒否する。取り違えて古い方針を現行の方針と誤読するのを
  防ぐため。保護モードの取り込みは専権キーを無視して警告する。
- 非保護モードでは値は毎ラウンドのレポートで上書きされる。**書き忘れると未決定へ倒れて `clean` を妨げる**
  （fail-close 側）。主文脈がオーナーの決定をレポートへ転記する。保護モードでは台帳の値を保持し、
  主文脈が `decide` で決定を記録する（下記「`ingest-reviewer` / `decide` / `activate`」）。

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

**非保護モードの保護水準は `disposition` 系と `scope` で 1 段違う。** 前者は記録だけを強制し、
後者は記録すら強制していない。保護モードの申告原本とオーナー確定の印は後述する。

#### `disposition` 系（`waived` / `deferred`）——記録は強制、オーナー判断は非強制

- `waived_by` / `waived_reason` は自由記述のスカラであり、**書いた主体がオーナー本人かを
  機械側は区別しない**。`ingest-review` を実行するのは主文脈（AI）であり、
  `.claude/hooks/agent-command-gate.sh` と `.codex/hooks/agent-command-gate.sh` の
  ロール別許可表が `ingest-review` を当事者ロールから締め出す。
- `deferred_to` は形式（`#123` / `123` / URL）だけを検査し、**指す Issue が実在するかは
  検証しない**。
- **したがってこの 2 つについて強制しているのは記録であって、オーナー判断ではない。**
  この結び（「強制しているのは記録」）は `disposition` 系にだけ掛かる。

#### 非保護モードの `scope` の覆し——記録の強制すら無い

- **`scope` の覆しがオーナーの判断であることを機械側は検証していない**（Issue #531）。
  台帳は取り込まれた `scope` の値を受け取るだけで、それが誰の判断かも、レビューアの元の申告と
  違うかも見ていない。**覆したこと自体を残させる欄も無い**ため、`waived_by` / `waived_reason`
  に相当する「記録の強制」も現時点では掛かっていない。書き忘れても verdict は動かないので、
  覆した値が黙ってレビューアの申告へ戻る（fail-open。再掲の規律＝
  `.ai/skills/issue-pipeline/SKILL.md` ②-c）。
- **検出できない窓は「その finding が台帳へ初めて取り込まれるラウンド」である**——
  ラウンド番号ではなく「その finding について前ラウンドの記録が台帳にあるか」で決まる。
  `pr-reviewer` の finding は主文脈を経て取り込みレポートになるため、**その finding についての
  最初の `ingest-review` より前**に書き換えられると元の申告値がどこにも残らない。
  `pr-reviewer` は各ラウンドで新しい finding を起票できる（ブロック見出しが
  `### F-<issue>-<seq> または new`＝`.ai/agents/pr-reviewer.md`）ため、**round 3 で初出した
  finding にも round 1 とまったく同じ窓が開く**。
  - **Issue #375 がこの窓を塞ぐ**。Claude Code の `pr-reviewer` は handoff ファイルから
    `ingest-reviewer` で取り込み、Codex を使う場合は信頼された外側の `codex_worktree_exec` が
    保存済み出力をそのまま同じ verb へ渡す。申告 scope の原本が初出ラウンドから
    `tmp/_karte/issue-<N>.declared-scope.jsonl`（追記専用）に残る。`decide --scope` の印がある
    finding はオーナーの値を保持し、今回の申告と異なれば取り込み出力に列挙する。
  - 覆しに `override_ref`＝`feedback_ledger` の台帳エントリ参照を要求する変更は Issue #523 のスコープ。
  - `codex_worktree_exec` は Codex 本体の read-only 権限を変えず、取り込みをラッパー側で実行する。
    Codex の `pr-reviewer` 自身に karte の書込権限は与えない。

### `ingest-reviewer` / `decide` / `activate`（Issue #375）

- **`ingest-reviewer --from tmp/_handoff/pr-reviewer--<key>.md [--round <R>]`**：`pr-reviewer` の
  finding を取り込む専用 verb。Claude Code は本人が実行し、Codex 実行時は外側ラッパーが Codex の
  出力ファイルを変更せず handoff へ保存して実行する。ID 重複・未知 ID・harm/scope 必須・distinct_from を検証し、
  保護モードの共通規則と次の制約を適用する。
  - `--issue` は受けない。Issue は進行ポインタで決まる。round は省略時に「ポインタの round ＋ 1」だが、
    通常は `--round` を省略し、ポインタの次 round を使う。明示値は台帳の最新 round と同じ場合に限り
    受け付ける。後退・飛び越しは拒否し、別 Issue の台帳へ書く経路は作らない。台帳に当該 round が既に
    入った後の再実行の可否は `--round` の指定と handoff の内容による（条件と回復は下記
    「進行ポインタの書込みが台帳より後に失敗した窓」）。
  - `--from` は `<repo-root>/tmp/_handoff/pr-reviewer--<英数._->.md` の通常ファイルだけ
    （`..`・symlink 構成要素・別ディレクトリ・別名を拒否。規則は `karte/handoff_path.py` に 1 箇所で、
    Write フックと共有）。
  - 処置方針はオーナー専権であり、レポート中の `disposition` / `deferred_to` / `waived_by` /
    `waived_reason` は finding ブロック内なら空値も含め無視して警告する。前書きの専権キー行は無視せず拒否する。
    台帳の値は保持する。
  - 保護モードの取り込みごとに、申告レポートで再掲されたかにかかわらず、オーナー印を台帳の全 finding へ
    再適用する。印がない finding の scope は新しい申告で更新する。
    申告の原本は台帳より先に追記する。
  - **台帳の書込みが失敗した窓（F-375-22）**：原本を台帳より先に作る順序は意図的で、逆順（台帳→原本）にすると
    原本のない台帳だけが更新された無保護の round が残る。代償として、原本の作成後に台帳の書込みが失敗する
    （ENOSPC・読取専用ファイルシステム・競合）と、台帳にその round が無いまま原本（その round の申告を含む）
    だけが残る。取り込みは拒否（fail-close）で終わり、進行ポインタは進まず期待値も消費されない。
    この状態では、原本が追記専用で消えないため、待機取消（期待値なしの `activate`）でも従来動作には戻らず、
    主文脈の `ingest-review` は保護モード（新規 finding の追記専用）になる。回復は同じ handoff で
    `ingest-reviewer` を再実行する（期待値が残り、台帳の最新 round は進んでいないので同じ round として
    受理され、原本の同一記録は重複しない）。この回復が効くのは、台帳に当該 round がまだ無いからである
    （`### new` の finding も、再実行で同じ ID を採番し直せる）。`decide` は `disposition` と `scope` しか更新できず、
    round 1 でこの窓に入った場合は台帳自体が無いので失敗する。回復の代わりには使えない。
  - **進行ポインタの書込みが台帳より後に失敗した窓**：`ingest_locked` は台帳を書いた後でポインタを進める。
    ポインタの書込みだけが失敗すると、台帳には当該 round の finding が入ったまま、ポインタは前の round に残り、
    期待値も消費されない（取り込みはエラーで終わる）。再実行の可否は `--round` の指定と handoff の内容で変わる。
    - `--round` を省略すると、ポインタの次 round が台帳の最新と同じになり、handoff の内容によらず
      「round は単調増加」で拒否される。
    - 台帳の最新 round を `--round` で明示すると、`### new`（または次に採番できる明示 ID）で
      台帳に入った未解消 finding と同一の指摘（summary の正規化文字列が完全一致すれば locus を問わず、
      それ以外は locus が交差し summary の類似度が閾値以上）を再発番する handoff は、
      「ID 再発番を検出」で拒否される（`ingest_accept.collect_accepted`）。**既存 ID の再掲だけの handoff は
      同一 round 許可（`allow_same_round`）を通って成功しうる**が、同じ round の再取り込みは台帳の状態遷移を
      壊しうるので回復手段として選ばない。
    - **回復はいずれの場合も再実行を使わない。** 主文脈が `python3 -m karte render --issue <N>` で
      当該 round が台帳に入っていることを確かめ、`activate --issue <N>`（次のレビューなら期待値の 5 引数つき）で
      ポインタを台帳の最新 round へ向け直す。この回復はポインタと期待値だけを直し、台帳の finding は変えない。
- **`activate --issue <N> [--run-id R --target-key K --snapshot-oid OID --input-digest D --phase P]`**
  （主文脈専用）：進行ポインタを対象 Issue へ向ける（round は取り込み済みの最新、台帳が無ければ 0）。
  初回の `ingest-reviewer` の前に実行する。5 つの envelope 引数は**全部同時に**与え、review handoff の期待値として
  ポインタへ記録する（下記「review handoff の共通 envelope」）。1 つも与えなければ期待値なし（レビューア待ちの解除）。
  `--repair-declared-scope` は envelope 引数のいずれとも同時指定できず、一部だけの指定も拒否する。
  **`activate` はどちらの形でも申告 scope の原本を作らない**。原本を作るのは、検証を通ったレビューア本人の
  取り込み（`ingest-reviewer`）だけで、原本は 1 件以上の申告があるときにだけ作られる。finding ブロックが 0 件の
  レポートは `model.parse_review` が原本の作成より前に拒否するので、申告 0 件で空の原本が残ることはない
  （0 件の初回レビューを取り込めない件は別 Issue #801）。ただし上記の台帳書込み失敗の窓（F-375-22）では、
  取り込みが成功していなくても原本が残りうる。
  待ちの間は、進行ポインタに残る期待値を守るため、主文脈の旧 `ingest-review` はどの Issue 宛でも拒否する
  （他 Issue 宛・round 1 を含む・F-375-03/49）。原本が無くても保護は途切れない。待機中の Issue の
  `ingest-reviewer` を待つか、`karte activate --issue <待機中の Issue>`（期待値なし）で待ちを取り消す。
  レビューア取り込み前に取り消した場合は原本が無く、
  主文脈の `ingest-review` は従来動作に戻る（退避経路を追記専用にしない・F-375-10）。レビューアが既に取り込んで
  原本がある Issue（F-375-22 の窓で原本だけが残った Issue を含む）では、待ちを取り消しても原本は消えず
  保護モードが残る（オーナー確定の scope を守るため）。
  主文脈の先書きは許されるが reviewer の申告ではない。書き手と原本の照合方法は下記「scope の出所」。
  `run_id` / `target_key` は handoff ヘッダへそのまま往復できる値（英数字で始まる 128 文字以内の
  英数字と `. _ : / @ + # -`）に限り、空白・`-->` を含む値は `activate` が拒否する（F-375-12）。
- **review handoff の共通 envelope（Issue #375・#371 契約）**：handoff 先頭の 1 行
  `<!-- handoff issue=N round=R schema=review-handoff/v1 schema_version=1 producer=pr-reviewer phase=P
  artifact_type=ReviewReport run_id=X target_key=Y input_digest=<sha256> snapshot_oid=<40hex> status=ready -->`
  が #371 の共通項目（schema version・producer・phase・issue・run_id・target_key・input digest・snapshot OID・
  artifact type・status・next expected artifact＝review では常に空）を持つ。review 固有の 9 項目 finding は
  本文（payload）のまま。`ingest-reviewer` は申告を、**主文脈が `activate` でポインタへ記録した期待値**
  （Codex 経路では承認済み binding の `expected` と検証済み `artifact_digest` から作ったヘッダ）へ完全に束縛し、
  別 run・別 target・古い snapshot・別 digest・別 phase・未知／重複／欠落キー・`status` が `ready` 以外は
  取り込まない（共通語彙の実装は標準ライブラリだけの `karte/review_envelope.py`。`issue_envelope.review_envelope` は再公開で、
  束縛キーが `issue_envelope.handoff.BINDINGS` と一致することは単体テストが検査する）。期待値は**取り込み成功で消える 1 回限り**
  なので、取り込み済み handoff の再利用も拒否される。期待値の無い取り込みも拒否（fail-close）。
  期待値は進行ポインタの 1 枠だけに保持するため、残っている間は他 Issue 宛も含め主文脈の `ingest-review` を
  拒否する（round 1 でも期待値とレビューアの申告原本を守る）。申告原本のない scope（主文脈取り込み由来）を
  レビューア申告が置換したときは取り込み結果に
  `申告原本のない scope をレビューア申告で置換: <ID>（旧→新）` と出す（検出）。
- **再掲漏れの終了コード（F-375-05）**：保護モードは再掲漏れを警告つきで引き継ぐ。このうち**レビューアが過去に
  申告した（原本がある）是正対象の未解消 finding**（`needs_remediation`）が今回の `ingest-reviewer` 出力に
  再掲されていないときは、台帳は書き込み済み・未解消のまま引き継ぐが、**終了コード 5（`EXIT_INCOMPLETE`）**で
  返し、標準エラーに `未完了: 再掲漏れ <ID>`、標準出力の最後に `未完了（取り込み済み）: …` を出す。出力の欠落
  （切り詰め等）を終了コード 0 の完了にしないため。Codex wrapper は 5 を取り込み失敗
  （`CODEX_REVIEW_INGEST_FAILED`・終了コード 2）と区別し、`CODEX_REVIEW_INGEST_INCOMPLETE`（終了コード 5）として
  「取り込み済み・未完了（round は記録済み・期待値は消費済み）」を返す。同じ handoff を再取り込みせず、主文脈が
  `activate` で期待値を記録し直して再レビューする（F-375-11）。主文脈が足した finding・申し送り／処置不要と決まった finding の不在、
  主文脈専用の追記専用モードは対象外（警告のみ・終了コード 0）。再掲漏れは解消ではなく、取り込み済みの round を
  やり直さず、次のレビューで `status: open|resolved` を明示して再掲させる。
  5 の定義は `karte/exit_codes.py`、`cli.py` のモジュール docstring の終了コード一覧にも載せている。
  Codex wrapper の終了コード一覧（5 は `pr-reviewer` 専用の予約値）は `codex_worktree_exec/README.md`「終了コード」。
- **`decide --finding <ID> [--disposition … --deferred-to … --waived-by … --waived-reason …] [--scope in|out]`**
  （主文脈専用）：オーナー決定を台帳へ直接記録する。`disposition` の付随キー規則は `ingest-review` と同じ。
- **保護モード**：`ingest-reviewer` は常に、申告原本がある Issue（レビューア本人の最初の取り込みが作る）の
  主文脈専用 `ingest-review` も保護モードで動く。両経路で台帳の `disposition` 系とオーナー確定済み `scope` を保持し、専権キーを
  無視して警告する。前ラウンドの未解消 finding の再掲が漏れた場合は変更せず未解消のまま引き継ぎ、
  ID を警告する。解消は `status: resolved` の明示宣言だけである。警告は標準エラーに `警告: …`、
  取り込み結果の標準出力にも対象キー・行と引き継いだ ID を出す。
  保護モードの主文脈 `ingest-review` は新規 finding の追記専用である。既存 ID を再掲すると全件拒否し、
  台帳・原本・進行ポインタを書かない。既存の未解消 finding を省略した場合は引き継いで警告する。
  レビューア本人の `ingest-reviewer` は既存 ID を再掲できる。
  主文脈の `ingest-review` は従来どおり `--issue` / `--round` / `--from` を受け、handoff パス・
  ヘッダ・進行ポインタによる入力制約を課さない。新規 finding はレポートの scope で追加し、
  disposition は未決とする。主文脈による追加はレビューアの申告ではないので申告原本に記録しない。
  原本が壊れている場合は拒否する（終了コード 4）。原本がまだ無い場合の `ingest-review` は
  非保護モードであり、従来どおり専権キーを上書きし、再掲漏れを K-06 で拒否する。
  Codex の agent-command gate は `pr-reviewer` に karte verb を許可しない。Codex 経路では
  `codex_worktree_exec` の外側が同じ検証・取り込みを実行する。
- **handoff ヘッダ**：レポートの先頭（最初の `### ` より前）に `<!-- handoff issue=<N> round=<R> -->` の
  1 行が必須。進行ポインタから決まる取り込み先の Issue と取り込み先の round（`--round` 省略時はポインタの次の round、
  明示時はその値。`check_header` は解決後の round と照合する）に一致しないもの（ヘッダ無し・別 Issue・
  古い／再利用した handoff）は取り込まない（`### new` だけのレポートで別 Issue へ書く取り違えを防ぐ）。
- **Codex 起動手順**：既存の承認済み工程レビューは、trusted caller が primary checkout から
  `python3 -m issue_start.readonly_workspace --source <primary> --approval-file tmp/<approval>.json --role pr-reviewer -C <登録済みlinked worktree> --prompt-file tmp/<prompt>.md --output-file tmp/<未作成output>.md --binding-file tmp/<承認済みbinding>.json --model <model> --reasoning-effort <effort>` を実行する。
  readonly入口が承認・binding・入力を検査して linked worktree から executor を起動する。D5 により executor の `-C` と cwd の Git toplevel は一致しなければならず、primary checkout から `codex_worktree_exec` を直接起動する形は拒否される。
  prompt/output/binding は呼び出し側が既存契約に従って用意し、output は未作成の一意なパスを使う。一般 PR レビューで
  承認済み artifact binding を用意する方法は確認できていないため、信頼検査を緩めず起動を停止する。Codex 非ゼロ終了、空出力、進行ポインタ不在・
  Issue/最新 round 不一致、ヘッダ不一致、取り込み失敗では run を完了扱いにしない。正常終了後、wrapper は
  ポインタの Issue と次 round からヘッダを決め、Codex 本文は加工せず、目印行が無ければ先頭に付けて primary checkout の handoff へ保存し、
  `ingest-reviewer` を実行する。呼び出し側へは `取り込み済み: <path> (issue-N round R)` の1行と、取り込み出力の警告行だけを返す（判定の要約は含めない）。
- **オーナー確定の印**：`decide --scope` は申告 scope の原本に `by: owner` の印を足してから
  台帳の scope を更新する。印の保存後に台帳書込みが失敗した場合は、印を保存済みと再適用手順をエラーに表示する。
  次の `decide` または保護モードの取り込みで台帳へ反映する。保護モードの取り込みは毎回、再掲の有無にかかわらず
  オーナー印を台帳の全 finding へ適用する。印の保存自体が失敗した場合は台帳を更新しない。
  印のある finding の scope は保護モードが上書きしない（レビューアの申告は
  原本として記録するだけ。保持した finding ID は取り込み出力に列挙される）。印の無い finding では、
  台帳の値が `ingest-review` 由来でもレビューアの申告が正当な訂正として反映される。
- 申告 scope の原本（`tmp/_karte/issue-<N>.declared-scope.jsonl`）への追記は、既存の全行を検証したうえで
  全体を一時ファイル経由で置換する（途中までの行を作らない）。一時ファイルと置換後の親ディレクトリを
  fsync して置換を永続化し、電源断による長さ0・切り詰めを防ぐ（バックアップ公開時も同様に同期する）。壊れていれば `ingest-reviewer` は
  復旧手順を示して拒否し、主文脈が `python3 -m karte activate --issue <N> --repair-declared-scope` で
  原本だけを修復する。このオプションは envelope 引数と同時指定できない。進行ポインタを動かさず、壊れた行だけを除く（元は `.bak`、
  `.bak.1`、`.bak.2` … と世代を分けて残し、上書きしない）。
  自動修復できるのは原本全体を UTF-8 として読める場合に限る。不正な UTF-8 は拒否し、
  原本を変更せず、バックアップも生成しない。
  バックアップの保存後に原本の書込みが失敗した場合（symlink の検出など）は拒否されるが、
  本処理は保存済みのバックアップを削除しない。
  申告 scope の読取り・追記・修復は `tmp/_karte` をディレクトリ記述子で固定して行い、
  置き場の差替えを検査で検出した場合は拒否する。この保護は scope 原本とそのバックアップに
  限り、writer lock・カルテ本体・進行ポインタまで同じディレクトリを使うことは保証しない。
  修復の最終置換直前に置き場が差し替わると、置換後の検査で拒否しても、固定済みの元ディレクトリ
  内の原本は更新済みの場合がある。一時ファイルやバックアップが別途差し替えられていなければ、
  読取り時の元データを保存したバックアップは残る。
  同じディレクトリへ非協調に書き込める主体が一時ファイルや原本・バックアップを差し替える場合、
  原本・バックアップの整合性は保証しない。例えば一時ファイルを symlink に差し替えられると、
  バックアップ自体が symlink となり元データが保存されないことがある。これは sandbox やアクセス権
  による隔離の代替ではない。
  `pr-reviewer` はこの verb も原本も触れない。
- `--round` 省略時の round は進行ポインタの `round`（0＝未取込。欠落・非 ASCII 数字・負数・Issue 不一致は拒否）＋1 で、ロックの内側で決める。
  台帳が無い Issue の `activate` は round 0 を書くため、その直後に主文脈の `ingest-review` で
  `--round` を省略すると round 1 として取り込む。`ingest-reviewer` も round 0 を自動導出に使う。
  明示した `--round 0` は拒否する。
  保護モードの `ingest-review` は最新 round の明示で同じ round に追記できる。
  ポインタが遅れて省略値が台帳の最新 round と一致した場合も同じ round への追記になる。小さい round は
  拒否し、省略値が次 round なら次 round を使う。範囲外指摘の追記には最新 round を明示する。
  オーナー確定の印で覆しを判定するため、台帳書込みの失敗後に同じラウンドを再試行しても、
  レビューアの新しい scope をオーナーの覆しと誤判定しない。
- `decide` / `activate` / `ingest-review` はどのロールの許可集合にも入れない
  （`agent-command-gate.sh` の `KARTE_SUBCOMMANDS_BY_ROLE`）。`issue-fixer` の許可 verb は従来どおり
  `render`/`append`/`close-attempt`/`check`/`status`。

カルテの改ざん防止（`karte/model.py` の「改ざん防止の機械的裏付けと既知の限界」）と同じく、
静的検査で閉じきれない面はプロンプト規律・レビュー分離・GitHub 側の保護と併用して塞ぐ
（Issue #129）。

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
している穴が形を変えて再発する。よって `deferred`/`waived` は `status: open` のまま台帳に残し、
**「是正を要する finding」の集合からだけ外す**（`Finding.needs_remediation` が偽になる）。
この除外は verdict だけの話ではない——verdict・`check` の診断網羅要求・無進捗検知（`escalate`）の
3 経路が同じ 1 つの述語を共有する（次節）。

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
`expected`/`recheck`）を揃える。主文脈がそれを finding ブロックへ写して `ingest-review` する。
保護モードでは最新 round を `--round` で明示して追記し、レビューアの申告原本には記録しない。
**取り込みの実行は主文脈**で、是正当事者には
`ingest-review` を許さない（`.claude/hooks/agent-command-gate.sh` と
`.codex/hooks/agent-command-gate.sh` のロール別許可表）。

## `harm_detail` の内容 lint（Issue #511）

### なぜ入れたか（混入の実例）

`harm_detail` は **放置したときに何が壊れるか** だけを書く欄である。ところが実運用では
**処置方針（disposition）と判断経緯**が同じ欄へ書かれ、そのまま台帳へ入った（PR #509 /
Issue #431 のレビュー。`F-431-07`「…本PRの差分範囲外の既存行における既存パターンで、
新規追加テストによる新規発生ではない」＝対応不要と判断した理由、`F-431-02`
「…（オーナー確認済み・…で fix-here）」＝プロセス上の経緯）。

これは書き手の不注意だけが原因ではなく、**契約が誤指示を出し、機械検査がそれを通す**
という構造に支えられていた——`.ai/agents/pr-reviewer.md` は「処置方針はオーナー専権であり
書かない」と述べる一方、同じ節で「別 Issue にすべきだと考える場合も…**harm_detail と
expected に書いて**返す」と指示していた。Issue #511 は契約側（自己矛盾の除去・`harm_detail` に
書ける内容の限定）と機械側（本 lint）の**両方**を同時に塞ぐ。

### 何を拒否するか

`ingest-review` は `harm_detail` に次の語彙を検出したら、他の検証エラーと同様に
**レポート全体の取り込みを拒否**し（fail-close）、該当行と検出語を示す。

| 区分 | 語彙（`karte/model.py`） |
|---|---|
| 処置方針（`DISPOSITION_TERMS`） | `対応不要` / `処置不要` / `修正不要` / `対応は不要` / `別 Issue` / `別の Issue` / `申し送り` / `繰り越し` / `据え置き` / `次スプリント` / `本 PR で直す` / `fix-here` / `deferred` / `waived` |
| 判断経緯（`PROCESS_TERMS`） | `オーナー確認済み` / `新規発生ではない` / `差分範囲外` / `スコープ外` |

- 照合は決定論的な部分文字列一致。前処理で ASCII 大小文字を畳み、空白を除去するので
  「別 Issue」と「別Issue」は同一視される。形態素解析器のような外部依存は持てない
  （標準ライブラリのみ）。
- **書き換え先**：`harm_detail` には放置時の実害そのものを書き直す。決まったオーナー判断は
  `disposition` / `deferred_to` / `waived_reason` へ（レビュー担当が書く欄ではない）。
  別 Issue にすべき等の**見立てはどの欄にも書かない**——レビュー担当の申告は `scope: out` まで
  である（`.ai/agents/pr-reviewer.md`）。`expected` は「期待する観測可能な状態」を書く欄であり、
  見立ての退避先ではない。
- **適用範囲は新規の `ingest-review` / `ingest-reviewer`**。既存カルテを読む側（`karte/model.py` の
  `parse`）には掛けない——`tmp/` は版管理外だが、進行中の Issue の台帳が読めなくなると
  是正ループが止まる（`scope` 必須化と同じ移行方針）。

### false positive の抑制（`karte/allowlist.py`）

部分文字列一致である以上、**実害そのものを述べるためにその語を使わざるを得ない**ケースが
原理的に残る（例：`karte` 自身をレビューしたときの「`deferred` の finding が診断網羅から
外れない」）。その場合は `karte/allowlist.py` の `ALLOWLIST` へ
`AllowlistEntry(issue=..., term=..., harm_detail=..., reason=...)` を追加する。

- **`reason` は必須**。空のまま登録すると `ValueError` でモジュールの import 自体が失敗する
  （理由なき例外登録を作れない）。`time_fixture_lint/allowlist.py`・
  `asset_parity/exceptions.py` と同じ「消さず理由を残す」運用。
- 抑制の粒度は **`harm_detail` の全文一致**。語彙単位や Issue 単位で抑制すると
  「一度例外を認めた語は以後その Issue のあいだ書き放題」になり、lint が塞いだはずの経路が
  そのまま開く。文面を書き換えたら登録し直す必要がある（＝再承認が要る）ことは、
  この粒度の意図した性質である。
- **まず言い換えを試すこと**。allowlist は逃げ道ではなく、言い換え不能を記録する場所。

### 既知の限界（語彙一致の取りこぼし）

決定論的な語彙一致なので、**語彙表に無い言い回しの処置方針は通る**（fail-open 側）。
本 lint は「観測された混入の型を確実に捕まえる」ことを狙ったもので、処置方針の混入一般を
機械的に完全排除するものではない。契約（`.ai/agents/pr-reviewer.md`）・レビュー分離と
併用する（`karte/model.py` の「改ざん防止の…既知の限界」と同じ多層防御の考え方＝Issue #129）。

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
`4` 前提違反・検証失敗（fail-close）。加えて `5`（`EXIT_INCOMPLETE`・定義は `karte/exit_codes.py`）は
`ingest-reviewer` が台帳へ**取り込み済み**だが、過去に申告した是正対象の未解消 finding の再掲漏れがあり
完了扱いにしない印（失敗ではない。台帳は書き込み済みで期待値も消費済み・Issue #375）。
主文脈専用の保護モードの `ingest-review` は再掲漏れを警告するだけで、終了コード 5 の対象外である。

次の入力は例外（traceback の終了コード 1）ではなく `4` で拒否する（上の 4 種に収まる）：

- **不正な UTF-8 の入力**（レポート本文のファイル・標準入力、台帳、進行ポインタ、`--diff-file`）。
- **整数は ASCII 数字だけ**：整数引数（`--issue` / `--round` / `--attempt`）、台帳・ポインタ内の整数
  （`rounds`・`resolved_round`・`round`・`issue`）、finding ID・見出し（`F-<issue>-<seq>`・`# Karte: issue-N`・
  `Attempt N`・`Result N`）の番号。`²` のような非 ASCII 数字や、`int_args.MAX_DIGITS`（18 桁）を超える
  桁数は `4`（Python の変換上限 4300 桁ちょうどは `int()` を通り、`+ 1` した値の `str()` が `ValueError` になる）。
  変換の入口は `karte/int_args.py` の `ascii_int_or_none` / `require_ascii_int` / `parse_int` に
  一本化してある。`+ 1` して書く値（`ingest-review` の `--round` 補完・finding の連番・Attempt 番号）は、
  足した結果も読み戻せる桁数でなければ `4` で拒否する（書けば台帳が以後読めなくなるため）。
- **進行ポインタ `tmp/_karte/active.json` の JSON が壊れている／ネストが深すぎる**（再帰上限の
  `RecursionError` も `4`）。JSON オブジェクトでない中身も `4`。末尾改行付きの `--issue $'5\n'` も `4`
  （検査は `fullmatch`・正規表現の末尾は `\Z`）。`render` の見出しに出す `round` も、`append` の補完と同じ
  読み方（`pointer_completion.recorded_round`）で検証し、整数でない値は `4`（subagent の文脈へ注入される本文に
  検証前の値を出さない）。ポインタが別 Issue を指す・`round` が 0/欠落のときは見出しに出さない。
- **ロック内で拒否された `ingest-review`／`ingest-reviewer`** は共通経路 `ingest_locked` で、どちらも
  `4` を返し台帳・ポインタは書かないが、新規 repo でも `tmp/_karte/` と `.writer.lock` は残る。
  何も作らずに拒否できるのは、ロック前に行う引数・ポインタ・本文の検証だけである。

### scope の出所（#797）

`tmp/_karte/issue-<N>.scope-origin.jsonl` は各 ingest の書込み前 `pending` と台帳書込み後
`committed` を対で保存する。各行は `tx`、`phase`、`round`、`entries`（`id`、`scope`、`source`、
`new`）を持つ。`source` は `main` または `reviewer`。申告原本とは別であり、
この記録は reviewer 申告を作らない。`activate` はどちらも作らない。

消費側は `karte.scope_origin.first_writers(issue, repo_root)` で最初の書き手を取得し、
`karte.scope_origin.reviewer_declarations(issue, repo_root)` で reviewer 申告の round と値を取得する。
辞書に ID がない場合、出所または申告は未証明であり、#523 の消費側は reviewer 申告なしを
「覆しなし」として clean にしてはならない。`unknown` も未証明として扱う。既存履歴や
書込み途中は `unknown` となり、途中失敗からの再試行でも先書き履歴を推定しない。
この API は現時点の scope の書き手ではなく最初の書き手と申告履歴を返す。
申告 API は出所記録で台帳への反映が確定し、かつ原本に存在する申告だけを返す。
原本自体の書込み後に台帳が失敗した申告は返さない。出所の確定書込みが台帳の保存後に
失敗した場合、台帳は保存済みでポインタは進まず、出所は未証明となる。再取り込みせず
`karte render` で台帳を確認し、`karte activate` でポインタを回復する。未証明の出所は
回復後も推測しない。出所記録の消失・破損は
保証を損ない、破損は拒否する。非協調なファイル操作からの完全性は保証しない。
