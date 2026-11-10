# karte handoff 検証の設計（Issue #683）

設計者＝Claude Code (AI)。**この文書は実装前の設計であり、実装は後続の是正ラウンドで行う**。Issue #683 の本文（Scope・AC・設計論点 a〜g・未決点 Q1〜Q3）を前提とする。K-01〜K-04 の分割（`.ai/rationale/karte-module-split.md`）を基盤とし、本 PR は第二弾である。**`maintainability_lint/baseline.json` は第一弾（PR #795〜#807）で更新済みで、本 PR では一切変更しない。**

## 1. オーナー確定（#683 の未決点）
| 未決点 | 確定 | 設計への反映 |
|---|---|---|
| Q1 外部投稿の事前確認 | **C**：verb は投稿内容をプレビュー表示し、確認を経て投稿する。確認なしの自動投稿はしない | `handoff-preview`（投稿しない）と `handoff-post`（プレビューの digest を確認トークンとして要求）に分ける。§4 |
| Q2 変更範囲 | **A**：handoff は無進捗（escalate）判定の計数からのみ除外する。verdict は不変 | `needs_remediation`・`check`・verdict は変更しない。無進捗の集計だけが別述語を通る。§6 |
| Q3 申し送り先が closed（completed）のとき | **A**：not planned と同様に計数へ復帰する | 再検証で closed（理由を問わない）を `invalid` にする。§7 |

オーナー承認の記録（この PR 本文にも載せる）：上記3点はオーナーが確定（#683 の本文末尾の原案どおり、Q1＝C・Q2＝A・Q3＝A）。ここで確定した判断を AI が覆さない。

## 2. 覆す既存設計と、残す保証範囲
- 覆す対象：`harm: none` の finding は `deferred` と書いても無進捗の計数から外れない（2026-09-07 オーナー確定。`karte/README.md`「`clean` の解除力は `harm: real` にだけ与える」）。
- 覆す根拠（#683 の本文と同じ）：解除条件を「`deferred` と書くこと」から「機械検証済みの転記が申し送り先に実在し、内容が現在の finding と一致し、申し送り先が open であること」へ置き換える。自己申告の2行では満たせない。**verdict の STOP（`no-harm-only` はオーナーへ打ち上げる）は維持する。**
- 保証するのは「記録が申し送り先に実在し続けること」まで。申し送りの適否はオーナー判断のまま。verb を実行するのは AI 自身なので、無関係な open Issue へ投稿して検証を通す余地は残る（Issue #129 と同種の限界）。ただし**行き先は `deferred_to` に結び付ける**（§4・§6。`--to` が `deferred_to` と食い違う投稿は拒否し、検証後に `deferred_to` が書き換わったら除外が外れる）。無関係な Issue へ投稿して除外を得るには、`deferred_to` もその Issue に向ける必要があり、`deferred_to` は台帳に残る。
- **確認トークンの限界（Q1＝C の担保範囲）**：トークンが証明するのは「投稿内容がプレビューと同一であること」までで、**オーナーが承認したことは証明しない**。同じ AI がプレビューを出してそのままトークンを渡せるため、承認の担保は `issue-pipeline` SKILL ②-c の手順（プレビュー全文と宛先をチャットで提示してオーナーの明示承認を得てから `handoff-post` を実行する。`.claude/main-context/01-owner-communication.md` と整合）に依存する。この手順は §9 の SKILL 更新に含める。

### 2026-09-07 確定の旧記述（移設・PR8 区分1）
書き換え（区分2）の前に、旧記述を次のとおり逐語で保全する。実装では README・docstring・SKILL を現行内容へ**書き換え**、この節へは追記しない。

`karte/README.md`「`clean` の解除力は `harm: real` にだけ与える（オーナー確定・2026-09-07）」：

```text
`harm: none` の finding に `disposition: deferred` / `waived` を書いても **verdict は動かない**
（記録としては残る）。`harm: none` の未解消がある間は verdict が `no-harm-only` のままになり、
「未解消がすべて実害なしになったらオーナーへ打ち上げる」STOP
（`.ai/skills/issue-pipeline/SKILL.md`「実害の定義とエスカレーション」）が生きる。

理由：`disposition` はそもそも「`harm: real` に対するオーナー判断の記録」として導入した
（Issue #495 の提案挙動 3〜5 はいずれも `harm: real` が主語）。解除力を `harm` の値によらず
与えると、実害なしの指摘に `deferred` と適当な Issue 番号を 2 行書くだけで verdict が
`clean` へ変わり、**AI が単独で既存のオーナー STOP を消せる**。それは本 Issue が塞いだ
「ラベルを書くだけで clean を通す」経路と同型のものを `harm: none` 側へ新設することになる。
```

`karte/__init__.py` のモジュール docstring の該当箇所：

```text
  無進捗検知にも同じく効く（下記「除外規則は 1 箇所に置く」）。**この解除力は ``harm: real`` にだけ与える**（オーナー確定・2026-09-07）
  ——``harm: none`` にも与えると、実害なしの指摘に ``deferred`` と書くだけで
  「未解消がすべて実害なしになったら打ち上げる」既存の STOP を消せてしまう。
  書式と移行措置の詳細は ``karte/README.md``。
```

`karte/karte_record.py::remediation_findings` の docstring（全文）：

```text
        """**この PR で是正が求められている未解消 finding**（Issue #503・単一の集合）。

        verdict の「``clean`` を妨げる未解消」（``status --json`` の ``blocking_findings``）・
        ``check`` の診断網羅要求・無進捗検知は、いずれもこの 1 つの集合を使う。
        除かれるのは **``harm: real`` かつ** ``deferred``/``waived`` のものだけ
        （:data:`CLEARING_HARM`）。``harm: none`` は ``disposition`` を書いても残る。
        """
```

`karte/__init__.py` のモジュール docstring「除外規則は 1 箇所に置く（Issue #503）」の段落（全文）：

```text
除外規則は 1 箇所に置く（Issue #503）:
  ``deferred``/``waived``＝「当該 PR では処置しない」と決まった finding を判定から外す規則は、
  :attr:`karte.model.Finding.needs_remediation` **だけ**に実装する。``status`` の verdict・
  ``check`` の診断網羅要求・無進捗検知（``escalate``）はこの 1 つの述語を共有する。
  Issue #495 の実装が除外を verdict 算出にしか入れなかったため、``check`` は
  ``deferred`` にも診断を要求して**毎ラウンド必ず 1 回 block**し（観測1）、無進捗検知は
  誰も直さないと決めた finding を拾って ``escalate: yes`` を偽陽性で出していた（観測3）
  ——同じ取りこぼしが経路の数だけ別々に開いた。以後 ``deferred`` を参照する判定を足すときは、
  この述語を経由させれば自動的に同じ規則が効く。
  併せて ``change_kind`` に ``doc``（文書のみの是正）を追加した（観測2。既存カルテの
  ``config`` 記録は遡って読み替えない＝``karte.model`` の :data:`~karte.model.CHANGE_KINDS`）。
```

`karte/README.md:86`（「既知の限界」の箇条書き）：

```text
- `deferred_to` は形式（`#123` / `123` / URL）だけを検査し、**指す Issue が実在するかは
  検証しない**。
```

`karte/README.md` の節「`deferred`/`waived` の除外は 1 箇所に置く（Issue #503）」（294-321行・全文。`_stalled_ids` は K-03 で `karte/stall_detection.py::stalled_ids` へ移っており、この引用は移設前の記述）：

```text
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
```

`.ai/skills/issue-pipeline/SKILL.md`「実害の定義とエスカレーション」：「**この解除力は `harm: real` の finding にだけ与える。** `harm: none` の finding に `disposition` を書いても記録が残るだけで verdict は動かない。」と、無進捗の項「**申し送り（`deferred`）／処置不要（`waived`）と決めた finding はこの計数から外れる**」。

**書き換え後の現行内容（実装で反映する）**：`clean` の解除力と verdict は従来どおり `harm: real` にだけ与える（`harm: none` の verdict は動かない）。**無進捗の計数だけは**、`harm: none`・`deferred` の finding が「検証済み handoff（申し送り先に実在し、内容が現在の finding と一致し、申し送り先が open）」を持つ場合に外れる。それ以外（`waived`、`harm: none` で未検証・無効の `deferred`）は従来どおり計数される。既知の限界は §2 の2点。

## 3. データ構造と書式（設計論点 b・c）
### 別フィールド（`status` 語彙は増やさない）
finding ブロックに**任意キー**を5つ追加する（`status` の語彙を増やすと `needs_remediation` を共有する verdict・`check` を巻き込むため）。

| キー | 意味 |
|---|---|
| `handoff_issue` | 申し送り先の Issue を **repository を含む正規形 `OWNER/REPO#N`** で記録する（番号だけにしない。下記「行き先の正規化」） |
| `handoff_comment_url` | 投稿したコメントの URL |
| `handoff_content_hash` | 転記ブロックの内容ハッシュ（`sha256:<64桁hex>`） |
| `handoff_verified_at` | 最後に検証した UTC 時刻（ISO 8601） |
| `handoff_state` | `verified` または `invalid`（空＝記録なし） |

- 既存カルテとの互換：キーは**すべて任意で既定は空**。記録を持たない finding は `render_finding` が**これらのキーを出力しない**（既存カルテの出力はバイト単位で不変）。`FORMAT_VERSION` は 1 のまま（追加は加法的）。**旧版の `karte`（ロールバック時）は未知キーを拒否せず無視する**（実コード：`block_records._finding_from_block` は既知キーだけを読み、`block_parser.parse_blocks` が拒否するのは重複キーだけ。レポート側の `parse_review` も未知キーを無視するので、§5 の明示的な拒否が要る）。旧版が新カルテを読んで書き直すと `handoff_*` が失われ、除外が効かなくなって**計数に戻る（fail-close）**。記録は復元できないので再度 `handoff-post`（§4 の冪等採用で既存ブロックを再利用）が要る。**`handoff_*` キーの綴り違いも無視されて除外が効かなくなる側（fail-close）に倒れる**。この前方非互換を README の「既知の限界」へ記す。
- 保存先を別セクションにしない理由：`parse` は未知セクションを拒否し、`ingest-review` はセクション単位で書き直すため、別セクションは保持の仕組みを別に要する。finding ブロックのキーなら `apply_accepted` が上書きしない限り**全件再掲を跨いで保持される**（`apply_accepted` は handoff 系キーに触れない）。
- ID 再発番：記録は finding オブジェクトに付くので、**再発番された新しい finding には引き継がない**（記録なし＝計数される。fail-close）。`id` をハッシュに含めるため、他 finding のブロックを流用しても照合に失敗する。

### content_hash の対象（設計論点 c）
対象は `id`・`harm`・`summary`・`locus`（要素を整列）・`expected` の5項目を、固定の区切りと正規化（前後空白の除去・改行を含まない）で連結した文字列の sha256。`evidence`・`harm_detail`・`recheck`・`severity` は対象外（再掲での言い換えで毎ラウンド無効化されて偽陽性が戻るのを防ぐ）。対象を絞りすぎて内容変更を見逃す側のリスクは、`summary`・`expected` を含めることで限定する。ハッシュ対象の追加・変更は `HANDOFF_HASH_VERSION` の更新と既存記録の無効化を伴う（ブロックに `hash_version` を載せる）。

### 転記ブロック（申し送り先のコメント本文）
```text
<!-- karte-handoff:v1 -->
Claude Code (AI) による転記（karte handoff）
- finding: F-683-01
- harm: none
- summary: <summary 全文>
- locus: <a.py::f, b.toml::g>
- expected: <expected 全文>
- hash_version: 1
- content_hash: sha256:<64桁hex>
<!-- /karte-handoff -->
```
- 冒頭の1行は、実行した AI agent 由来であることの明記（`.ai/guidance/common.md`「言語・対外記録」。設計論点 e）。agent 名は `--agent` の必須引数（許可集合 `Claude Code` / `Codex`）から取り、既定値を持たない。
- 読み戻しでは、**投稿された本文のブロックから各項目を取り出してハッシュを再計算し**、(1) ブロック自身の `content_hash` と一致、(2) 現在の finding から計算したハッシュと一致、の2つを検査する。**1コメント内**にブロックが複数ある・マーカーが無い・形式が違う場合は失敗（宛先 Issue 全体の既存ブロックとの関係は §4 の冪等性で定める）。
- **正規化規則（ブロック解析・ハッシュ計算の前に適用）**：改行コードは LF へ統一（CRLF・CR を変換）、各行の末尾空白を除去、本文全体の前後の空白行を除去。GitHub が本文を CRLF や末尾空白付きで返しても照合できるようにするため。ハッシュ対象の各項目は §3 の正規化（前後空白の除去）に従う。

## 4. verb と流れ（Q1＝C・設計論点 d・e・f）
`karte/handoff_cli.py` が `register(subparsers, add_issue)` を提供し、`__main__.py` の `extra_registrars` に追加する（`owner_cli`・`reviewer_cli` と同じ経路）。**`cli.py`・`parser_core.py` は変更しない**（`cli.py` の61行を保つ）。全 verb は `fail_close` でロック要否を宣言する。

| verb | 役割 | ロック（`gh` 呼び出しとの関係は下の「ロックと `gh`」） | GitHub | 台帳への書込 |
|---|---|---|---|---|
| `handoff-preview --finding <ID> --to <Issue> --agent <名>` | 前提条件（下記）を検査し、投稿予定の全文・宛先（`OWNER/REPO#N`）・**確認トークン**を出力する | なし | 読取りのみ（宛先が Issue であり open か） | なし |
| `handoff-post --finding <ID> --to <Issue> --agent <名> --confirm <確認トークン>` | 前提条件・確認トークンの一致を検査 → 既存ブロックの採用または投稿 → 読み戻し → ハッシュ照合 → 記録 | 観測（`gh`）は**ロックの外**、書込だけ**ロックの内** | コメント投稿・読取り | 照合成功時だけ `handoff_*` を書く |
| `handoff-recheck [--finding <ID>...]` | 記録を持つ finding の再検証（最終検証の入口） | 同上（観測はロックの外、書込だけロックの内） | 読取りのみ | 観測結果に従い `handoff_state` を `verified`/`invalid` へ |

### 前提条件（F-809-01：記録を行き先 `deferred_to` に結び付ける）
`handoff-preview`・`handoff-post` は、次をすべて満たす finding にだけ進む。満たさなければ**使用エラー（`KarteUsageError`）で何も投稿・書込しない**。
- finding が `status: open`、かつ `disposition: deferred` として**すでに決定済み**（`decide` または保護モード外の取り込みで `deferred_to` が記録されている）。`disposition` が未決定・`fix-here`・`waived` の finding は拒否する（申し送りの適否の判断はオーナーで、verb は決定済みの申し送りを検証するだけ）。
- `--to` が、正規形（`OWNER/REPO#N`。下記「行き先の正規化」）で finding の `deferred_to` と**一致**する。別 Issue 宛て・別 repository 宛ては拒否する（`deferred_to` を先に `decide` で直す）。
- `harm: none` の finding だけを対象とする（Q2＝A。`harm: real` の `deferred` はすでに verdict・計数から除外されており、handoff を除外条件に使わないので拒否する。記録だけを残す運用は設けない）。
- 宛先が自リポジトリの **Issue**（プルリクエスト・別 repository は拒否）。

### 行き先の正規化（F-809-08）
`DEFERRED_TO_RE` は任意のホスト・repository の `https://…/issues/N` を受け入れるので、**番号だけに正規化して比べない**。`karte/finding_handoff_target.py` は、**基準となる repository（`OWNER/REPO`）を引数で受け取る純関数**（git・gh・環境を一切読まない）で、次の規則で行き先を `OWNER/REPO#N` へ正規化する（F-809-11）。
- **基準 repository の取り方（判定を origin に依存させない）**：
  - **`is_stall_exempt`（status・render・check の経路）**：基準は、**投稿時に記録した `handoff_issue` の repository 部分**。現在の行き先 `deferred_to` を、この repository を基準に正規化して `handoff_issue` と比べる。したがって述語は **finding だけから決まる純関数**で、`git`・`gh`・origin を呼ばず、origin を持たない一時ディレクトリ・linked worktree でも従来と同じ出力になる（既存の `tests/unit/test_karte_*` への影響なし）。`stalled_ids(karte)` の引数は変えない。
  - **`handoff-preview`・`handoff-post`・`handoff-recheck`（verb 側）**：基準は **origin の repository**。**origin の導出はこれらの verb だけの責務**で、`finding_handoff_target` には持たせない。導出規則：`git remote get-url origin` を解析する（`https://github.com/OWNER/REPO(.git)`・`git@github.com:OWNER/REPO(.git)`・`ssh://git@github.com/OWNER/REPO(.git)` の各形式、末尾の `.git` は除去、owner・repo の大文字小文字は比較時に無視）。**origin が無い・host が github.com でない・解析できない場合は使用エラー**（何も投稿・書込しない）。実行する worktree は、台帳の所在（`main_worktree_root()`）ではなく**呼び出し元 worktree**（`repo_roots.invoking_worktree`。`close-attempt` が diff を測るのと同じ）とし、その `origin` を読む。
- 規則（基準 repository を `B` とする）：
  - `#N`・`N`：`B#N`。
  - `https://github.com/OWNER/REPO/issues/N`：ホストが `github.com` で、`OWNER/REPO` が `B` と一致する（大文字小文字を無視）場合だけ有効（正規形は `B#N`）。**ホストが違う・repository が違う URL は正規化できず**、`handoff-preview`・`handoff-post` は使用エラー、`is_stall_exempt` は不一致（計数に戻る）として扱う。
- 比較は正規形どうしで行い、`handoff_issue` も `OWNER/REPO#N` で記録する（投稿時に verb が origin から導出）。別 repository の URL の行き先 `deferred_to` と、自リポジトリの同番号への `--to` は一致しない。
- **`handoff_issue` の repository を verb が検証する**：`handoff-post` は `handoff_issue` の repository が origin と一致する場合にだけ記録し、`handoff-recheck` も観測前に `handoff_issue` の repository が origin と一致することを検査する（一致しなければ `invalid`）。status 側が記録の repository を信頼できるのは、記録を書くのが verb だけで（§5）、書込前にこの検査を通っているため。

検証後に `deferred_to` が書き換わったとき（保護モード外の `ingest-review` が毎ラウンド `deferred_to` を上書きする）は、**検証済み記録は残したまま、除外だけが外れる**（§6 の `handoff_issue == deferred_to` 条件）。ハッシュ不一致と同じ扱い。

### ロックと `gh`（F-809-02）
`writer_lock` の `flock(LOCK_EX)` にはタイムアウトが無く、`fail_close(locked=True)` は verb 全体をロック内で実行する。`gh` が応答しないままロックを握ると、全 karte verb（`status`・`check` を含む停止要件の判定）が待たされる。したがって次に固定する。
- **`gh` の呼び出しはすべてロックの外**で行う。`handoff-post`・`handoff-recheck` は `locked=False` の verb として宣言し、書込の短い区間だけ内部でロックを取る（`finding_handoff_store` が `writer_lock` を取り、その内側では `gh` を呼ばない）。
- 流れ：①ロック外で台帳を読み、前提条件を検査し、対象 finding の `content_hash` と `deferred_to` を控える → ②ロック外で `gh` を呼び観測する → ③ロックを取り、**台帳を再読込して**対象 finding の `content_hash`・`deferred_to`・`status`・`disposition` が①の値と一致することを再確認し、一致するときだけ `handoff_*` を書く → ④不一致なら**何も書かず**「観測後に finding が変わった。再実行すること」と `EXIT_ERROR`。`handoff-recheck` が `invalid` を書く場合も同じ流れ。
- **各 `gh` 呼び出しにタイムアウト**（`finding_handoff_gh_run` の定数。既定 30 秒、`subprocess` の `timeout`）を設け、超過は検証失敗として扱う（検証済みを書かない。recheck は `invalid` 側）。
- `verb_boundary` の `locked` 宣言と `require_declared` の整合：この2 verb は `locked=False` で宣言する。台帳への書込が `writer_lock` の内側に限られることは、`finding_handoff_store` の単体試験で固定する。

### 冪等性と部分失敗後の回復（F-809-03）
- **`handoff-post` は投稿の前に宛先 Issue の既存コメントを走査**し、同じ finding ID・同じ `content_hash` の転記ブロックを探す。見つかれば**新規投稿せず**、そのコメントを読み戻して照合し、検証できれば**採用して記録する**（冪等）。複数見つかった場合は先頭（最古）のコメントを採用し、残りは出力で通知する（削除しない）。
- **走査は全ページを取得する**（`gh api --paginate` 相当。取得を途中で打ち切らない。ページ取得の失敗は走査失敗＝検証失敗として扱い、**走査できていない状態で新規投稿しない**。先頭ページだけを見て既存ブロックを見落とし重複投稿するのを防ぐ）。
- **採用・再検証の対象は、認証中の `gh` ユーザー（`gh api user` の `login`）が投稿したコメントに限る**。コメントの `user.login` が一致しない他者投稿のブロックは、採用も `verified` の根拠にもしない（公開 repository で第三者が同じ finding ID・content_hash のブロックを投稿して採用させる経路を塞ぐ）。許可者を増やす設定は設けない（YAGNI）。他者投稿のブロックが先に見つかった場合は無視して走査を続け、自分の投稿が無ければ新規投稿する。`handoff-recheck` も同じ検査を行い、投稿者が一致しなければ `invalid` とする。
- 投稿後に失敗した場合（読み戻し・照合・台帳書込のどこでも）は、**作成済みコメントの URL を出力**して `EXIT_ERROR`。同じコマンド（同じ `--confirm`）を再実行すると、上の走査で作成済みコメントが見つかって採用されるので**重複しない**。タイムアウトでサーバ側にだけ作られていた場合も同じ。台帳書込だけが失敗した場合も同様（採用して書き直す）。
- コメントは verb が削除しない（削除は外部に見える操作で、オーナー判断）。
- **例外型と終了コード（F-809-07）**：`fail_close` が `EXIT_ERROR`（4）へ変換するのは `verb_boundary._REFUSALS`（`KarteUsageError`・`KartePathError`・`KarteFormatError`・`OSError`・`TouchedError`）だけで、`subprocess.CalledProcessError`・`subprocess.TimeoutExpired`・JSON 不正（`json.JSONDecodeError`/`ValueError`）は含まれず、変換されないと traceback と終了コード 1 で落ちて終了コード契約（0・2・3・4）を破る。そこで `karte/finding_handoff_errors.py` に **`FindingHandoffError(KarteUsageError)`** を定義し（`_REFUSALS` の型の派生なので `verb_boundary` を変更せず EXIT_ERROR に載る）、`finding_handoff_github` が**すべての失敗をこの型に包んで送出する**：非 0 終了（`CalledProcessError`）・タイムアウト（`TimeoutExpired`）・不正 JSON・想定外のレスポンス形・`gh` 不在（`FileNotFoundError`）・認証・レート制限・404 等（下の表の分類を例外の属性 `kind` に持たせる）。「観測後に finding が変わった」（§4 のロックと `gh`）も同じ型で返す。`verb_handoff_*` は `FindingHandoffError` だけを捕捉して表のとおり出力し、**それ以外の例外を握りつぶさず**、また `gh` 由来の例外を包まずに外へ出さない。`handoff-recheck` は finding ごとに `FindingHandoffError` を捕捉して `invalid` を書き、全 finding を処理した後に1件でも失敗があれば EXIT_ERROR を返す。新しい終了コードは作らない。
- **失敗種別**（`finding_handoff_github` が分類して `FindingHandoffError.kind` に持たせ、`verb_handoff_*` が表のとおり出力する）：

| 失敗 | 扱い | 台帳 |
|---|---|---|
| 認証（401・`gh` 未ログイン）・権限不足（403 でレート制限でないもの） | 検証失敗。`gh auth status` と権限の確認を促す | 書かない（recheck は `invalid`） |
| **レート制限（403・429。二次制限を含む）** | **権限不足と区別する**。応答ヘッダ（`x-ratelimit-remaining: 0`・`retry-after`）または本文の `rate limit` の文言で判別し、「待って再実行」と案内する（認証エラーと誤案内しない）。再実行は冪等 | 書かない（recheck は `invalid`） |
| 宛先 Issue 自体が 404・削除、または移転・repository 改名 | 失敗（宛先が存在しない・移転した旨）。**`gh api` は GET のリダイレクトを既定で追従し、止める指定が無い**ので、リダイレクトは追従されるものとして扱い、**レスポンスの `html_url`・`repository_url`・`number` が、要求した `repos/OWNER/REPO/issues/N`（`OWNER/REPO#N`）と一致するか**を検査する。一致しなければ移転・改名として失敗とし、移転先へ黙って切り替えない。コメントの読取りも、レスポンスの `issue_url` が要求した Issue と一致するかで同様に検査する。リダイレクトを避けるために `gh` 以外の HTTP 手段を使わない（標準ライブラリ・`gh` のみの方針を保つ） | 書かない（recheck は `invalid`） |
| コメント一覧のページ取得の失敗 | 走査失敗＝検証失敗（走査できていない状態で投稿しない） | 書かない（recheck は `invalid`） |
| 他者が投稿したブロック | 採用・検証の根拠にしない（認証中の `gh` ユーザーの投稿のみ） | 採用しない |
| 宛先 Issue が locked | 検証失敗。投稿できない旨を出す。既存ブロックの読取りで採用できる場合は採用可 | 採用時のみ書く |
| 宛先がプルリクエスト／別 repository | 使用エラー（前提条件）。投稿しない | 書かない |
| 5xx・タイムアウト・ネットワーク不可 | 検証失敗。再実行を促す（再実行は冪等。レート制限は上の専用行で扱う） | 書かない（recheck は `invalid`） |
| 本文の長さ上限（65536 文字）超過 | 投稿前に長さを検査して使用エラー（summary・expected が長すぎる finding は申し送りを分けるようオーナーへ） | 書かない |
| CRLF・末尾空白への正規化 | §3 の正規化規則を解析・ハッシュ前に適用。差は失敗にしない | — |
| 本文に `@name`（メンション）を含む | `handoff-preview` の出力に**警告**を出す（意図しない通知の可能性。オーナーが確認してから投稿する） | — |

### その他の運用
- **確認トークン**：投稿予定の本文・宛先・agent 名・finding の content_hash の sha256。オーナーがプレビューを確認した後に主文脈が `--confirm` へ渡す。プレビュー後に finding や本文が変わるとトークンが一致せず**投稿しない**。`handoff-post` は `--confirm` が無ければ使用エラー。**トークンは内容の同一性の担保であって、オーナーの承認の担保ではない**（§2）。

- **対象は自リポジトリの既存 Issue のみ**：宛先の repository は、verb が呼び出し元 worktree の `origin` から導出して固定し（導出規則は「行き先の正規化」。status・render・check は origin を読まない）、別 repository・新規 Issue 作成は対象外（新規 Issue は `/gh-create-issue` で作った後、その番号を `--to` に渡す）。
- **fail-close**：`gh` 不在・ネットワーク不可・非 0 終了・JSON 不正・タイムアウトは検証失敗として扱い、検証済みを書かない（上の失敗種別表）。
- **GitHub 呼び出しの境界**：`finding_handoff_github.py` が API を定義し、`finding_handoff_gh_run.py` が `subprocess` で `gh api` を実行する（標準ライブラリのみ）。実行関数を差し替えてオフラインで試験する。**`status`・`render`・`check` はネットワークを呼ばない**（設計論点 d。決定論を保つ）。
- **実行主体（設計論点 f）**：主文脈専用。`.claude/hooks/agent-command-gate.sh` と `.codex/hooks/agent-command-gate.sh` の `KARTE_SUBCOMMANDS_BY_ROLE` は許可リスト方式で、`issue-fixer` は `render/append/close-attempt/check/status`、`pr-reviewer` は `ingest-reviewer` のままとする（新 verb は**どのロールにも追加しない**＝既定で deny）。変更は不要で、**新 verb が両 gate で deny されることを試験で固定する**（Codex 側は `pr-reviewer` に karte verb を許可しない）。ゲートは sandbox ではない（既存の限界と同じ）。
- Codex 側 gate は `ctx_execute` / `ctx_batch_execute` をシェルツールとして検査しないため、これらの入力経路の deny はこの gate 単独では保証されない。
- 遡及（設計論点 g）：導入前に手書きで申し送り済みの Issue のコメントにはブロックが無いので、`handoff-preview`→`handoff-post` でブロックを投稿し直す運用。読み戻しモードは設けない（手書き本文の転記一致は機械照合できないため）。

## 5. `ingest-review` と レポート入力
- 全件再掲を跨ぐ保持：`apply_accepted` は `handoff_*` に触れない。内容が変わらない再掲では記録が残り、ハッシュも一致するので計数から外れたまま。内容が変わる再掲では記録は残るが**ハッシュ不一致で除外が効かなくなる**（再 `handoff-post` で新しいブロックを投稿し直すまで計数に戻る）。
- レポート入力の拒否：`review_block`（`parse_review`・`ingest-reviewer` 共用）が `handoff_` で始まるキーを検出したら、**取り込みごと拒否**（`KarteFormatError`・fail-close）。記録は verb だけが書く。
- `decide`・`ingest-review` の保護モード・`activate` は挙動不変。

## 6. 述語と計数（設計論点 a・Q2＝A）
- `Finding.needs_remediation`・`Karte.remediation_findings`・verdict・`check`・`#614` の領域は**変更しない**。
- 新しい純関数 `finding_handoff_exemption.is_stall_exempt(finding)` を追加する。真の条件は**すべて**：`status == "open"`、`harm == "none"`、`disposition == "deferred"`、`handoff_state == "verified"`、`handoff_content_hash` が現在の finding から再計算したハッシュと一致、**`handoff_issue` が現在の `deferred_to`（現在の行き先を、**`handoff_issue` の repository 部分を基準に** `OWNER/REPO#N` へ正規化した後の値。`#N`・`N` は記録の repository とみなし、URL は host が github.com で repository が記録と一致するときだけ有効）と一致**（F-809-01・F-809-08・F-809-11）。述語は finding だけから決まる純関数で、origin・`git`・`gh` を呼ばない（origin の導出は verb だけの責務。§4「行き先の正規化」）。食い違い（`deferred_to` の書き換え・ハッシュ不一致）は、検証済み記録を残したまま除外だけを外す。`decide` や保護モード外の `ingest-review` が `deferred_to` を書き換えても、新しい行き先への `handoff-post` で再検証するまで計数される。
- `stall_detection.stalled_ids` は `remediation_findings()` から `is_stall_exempt` を除いて数える。`render` の `★無進捗` は `stalled_ids` を引くので**同じ判定に従う**（経路別の再実装をしない）。`status` の `stalled_findings`・`escalate` も同じ。
- **`#614` との整合**：`check` 側の決定（診断網羅要求の除外規則）はこの PR で変えない。`handoff_exemption` を単一点にしてあるので、#614 が検証付き除外を採る場合は同じ述語を `check` から呼べる。経路ごとに別規則を作らない。
- `status --json` には、除外された finding がある場合に限り `handoff_exempt_findings`（ID の配列）を追加する（無い場合はキーを出さず、既存の golden・消費者 `karte_notify` に影響しない）。本文出力にも同じ条件で1行を追加する。

## 7. 計数への復帰（AC：各場合に試験）
| 場合 | 検出と処置 |
|---|---|
| ハッシュ不一致（再掲で内容が変わった） | `status` 時に再計算して不一致 → 除外されない（ネットワーク不要・記録は残す） |
| `deferred_to` の書き換え（`handoff_issue` と不一致）・`disposition` が `deferred` でなくなった | `status` 時に判定して不一致 → 除外されない（ネットワーク不要・記録は残す） |
| 申し送り先が closed（completed・not planned とも。Q3＝A） | `handoff-recheck` が `closed` を観測 → `handoff_state: invalid` |
| コメントの削除・編集 | `handoff-recheck` が 404 または本文のハッシュ不一致を観測 → `invalid` |
| 宛先 Issue の 404・削除、または移転・repository 改名 | `handoff-recheck` が 404、または追従後のレスポンスの `html_url`・`repository_url`・`number` が要求した `OWNER/REPO#N` と一致しないことを観測 → `invalid` |
| コメントの投稿者が認証中の `gh` ユーザーと一致しない | `handoff-recheck` が不一致を観測 → `invalid` |
| `gh`・ネットワーク不可 | `handoff-recheck` が観測できない → `invalid`（保守側。再実行で観測できれば `verified` へ戻せる）。`status` は記録だけを読むのでネットワークは呼ばない |
| 申し送り先が open へ戻った・コメントが復旧した | 再実行した `handoff-recheck` が全条件を満たせば `verified` へ戻す |

最終検証の入口：`issue-pipeline` の合流前確認（②-d の `pr_merge_gate report` の前）に `python3 -m karte handoff-recheck` を実行し、`invalid` や不一致があれば出力で指摘する。実行は主文脈。SKILL の運用規定は §9。

## 8. モジュール分割（新規 Python module は100行以内・`dataclass` と具象ロジック class は別 file・連続4行以上の行コメント禁止）
命名は既存の `handoff_header.py`・`handoff_path.py`（レビュー handoff の取り込み用）と区別するため、本機能のモジュールは `finding_handoff_*` を使う。

| モジュール | 責務 |
|---|---|
| `finding_handoff_record.py` | `HandoffRecord`（frozen dataclass のみ。キー5つ） |
| `finding_handoff_keys.py` | キー名・`HANDOFF_KEYS`・`HANDOFF_HASH_VERSION`・レポートからの拒否判定 |
| `finding_handoff_hash.py` | `content_hash(id, harm, summary, locus, expected)`（純関数） |
| `finding_handoff_block.py` | 転記ブロックの生成と解析（純関数） |
| `finding_handoff_ledger.py` | ブロック（台帳の finding ブロック）との相互変換（`record_from_block`・`emit_lines`） |
| `finding_handoff_exemption.py` | `is_stall_exempt(finding)` |
| `finding_handoff_preview.py` | プレビュー本文・確認トークンの生成 |
| `finding_handoff_github.py` | `gh api` の対象・応答の検証と投稿・コメント読取・Issue 状態読取。実行関数を引数で差し替え可能 |
| `finding_handoff_gh_run.py` | `gh api` の実行・JSON 読取・失敗分類 |
| `finding_handoff_context.py` | verb 共通の台帳・origin・宛先・Issue 状態の前提検査 |
| `finding_handoff_observe.py` | コメント識別・照合・時刻・失敗メッセージの共通処理 |
| `finding_handoff_verify.py` | 読み戻し本文と現在の finding の照合（`VerifyResult` を返す） |
| `finding_handoff_result.py` | `VerifyResult`（frozen dataclass のみ） |
| `finding_handoff_store.py` | **ロック内の短い区間だけ**で、台帳を再読込し観測時の `content_hash`・`deferred_to` 等との一致を再確認してから記録の書込・`handoff_state` の更新を行う（台帳 I/O は `karte_loader`・`paths`・`writer_lock` 経由。ここでは `gh` を呼ばない） |
| `finding_handoff_errors.py` | `FindingHandoffError(KarteUsageError)`（`kind` 属性。`gh` 由来の全失敗を包む型。F-809-07） |
| `finding_handoff_target.py` | 行き先の正規化（`#N`・`N`・URL → `OWNER/REPO#N`。**基準 repository を引数で受ける純関数**で git・gh・環境を読まない。基準と異なるホスト・repository は無効。F-809-08・11） |
| `finding_handoff_origin.py` | `git remote get-url origin` の解析（https・ssh 形式・`.git`・大文字小文字無視。origin 無し・github.com 以外は使用エラー）。**verb（preview・post・recheck）だけが呼ぶ**。status・render・check は呼ばない |
| `finding_handoff_scan.py` | 宛先 Issue の既存コメントから同じ finding ID・content_hash のブロックを探す（冪等採用用の純関数） |
| `verb_handoff_preview.py` / `verb_handoff_post.py` / `verb_handoff_recheck.py` | 各 verb（`@fail_close` を宣言） |
| `handoff_cli.py` | 引数定義と `register(subparsers, add_issue)`（`parser_*` と同じ流儀で1ファイルに収める。100行を超えるなら `parser_handoff_args.py` に分ける） |

既存ファイルの変更（**各ファイルが100行以内に収まること**が条件。超える場合は責務で更に分割する）：
- `finding_record.py`（現70行）：`handoff: HandoffRecord | None = None` の追加。
- `block_records.py`（現88行・追加余地が小さい）：ledger のブロックから `handoff_*` を読む呼び出しを `finding_handoff_ledger.record_from_block` に委ねる（本体は増やさない）。
- `karte_render.py`（現72行）：記録がある場合だけ `finding_handoff_ledger.emit_lines` を呼ぶ。
- `review_block.py`（現84行）：`handoff_` キーの拒否を `finding_handoff_keys` へ委ねる。
- `stall_detection.py`（現15行）：`is_stall_exempt` を除外。
- `status_payload.py`（現46行）・`status_text.py`（現92行・追加余地が小さい。超えるなら `status_handoff_lines.py` を新設）：除外 finding の出力。
- `__main__.py`：`extra_registrars` へ `handoff_cli.register` を追加。
- `model.py`：公開名の再エクスポート（`HandoffRecord` 等）が必要なら最小限。入口は100行以内を保つ。

**`maintainability_lint` への見込み**：新規モジュールはすべて100行以内・`dataclass` は `finding_handoff_record.py` と `finding_handoff_result.py` の2ファイルだけで具象ロジック class を同居させない・連続4行以上の行コメントを作らない。したがって `python3 -m maintainability_lint check` は `violations=0 accepted_debt=58` のまま通る見込みで、**`baseline.json` の変更は発生しない**。既存ファイルの変更で100行を超える場合は新規違反（baseline 外）として check が失敗するので、その場合は分割で対処し、baseline は更新しない。

## 9. 文書の更新（PR8 区分1→区分2）
1. 先に §2 の旧記述（README の「解除力」節・README:86・README の除外の節（294-321）・`__init__` の2箇所・`remediation_findings` の docstring・SKILL の2記述）を、**実ファイルと逐語一致で**本ファイルへ保全する（本ファイルの §2 で実施済み。実装時に実ファイルと照合し、ずれがあれば書換え前に直す）。
2. `karte/README.md`「`clean` の解除力は `harm: real` にだけ与える」節を、§2 の「書き換え後の現行内容」へ**書き換える**（追記で覆さない）。覆す根拠・保証範囲（記録が失われないこと・確認トークンの限界）・既知の限界（§2・旧版が `handoff_*` を無視して書き直すと記録を失う前方非互換）・新 verb・`handoff_*` キー・計数復帰の表（§7）を載せる。
3. **無進捗の除外規則を「`needs_remediation` と同じ集合」と説明する他の記述も同じ PR で書き換える**（F-809-05）：
   - `karte/README.md:86`「`deferred_to` は形式だけを検査し、実在は検証しない」：`harm: none` の `deferred` については、検証済み handoff（`handoff-post`）が実在と内容を検査する、と現行内容へ。
   - `karte/README.md` の節「`deferred`/`waived` の除外は 1 箇所に置く（Issue #503）」（294-321行）の本文と表：「verdict・`check` は `needs_remediation` の単一集合を共有し、**無進捗だけが `finding_handoff_exemption.is_stall_exempt` を追加で除く**（単一点は `finding_handoff_exemption`）」へ。表の無進捗の行と `render` の `★無進捗` の所在は、実体に合わせて `karte/stall_detection.py` の `stalled_ids`（K-03 で `cli.py` の `_stalled_ids` から移動済み）へ直す。#503 観測1・観測3 の経緯は §2 に保全済みなので、README 側は現行の規則だけを書く。
   - `karte/__init__.py` のモジュール docstring「除外規則は 1 箇所に置く（Issue #503）」の段落（節名で指す。行番号は実装時に実ファイルで確認）：同様に書き換える。
   - `karte/render_finding_lines.py` の行コメント（16行目付近「無進捗の印も `_stalled_ids`（単一の判定）から引く」。`_stalled_ids` は K-03 で `stall_detection.stalled_ids` へ移動済みの旧名称）：「無進捗の印は `stall_detection.stalled_ids` から引く（`finding_handoff_exemption.is_stall_exempt` を追加で除いた単一の判定）」を指す3行以内のコメントへ直す。経緯は本ファイル §2 に保全済みで追加の移設は不要。書換え後 `grep -rn "_stalled_ids" karte` が、互換のための再エクスポート名（`karte/cli.py` の `_stalled_ids` 別名とそれを使うテスト）を除いて旧名称を残さないこと。
   - `karte/karte_record.py::remediation_findings` の docstring：「verdict・`check` は単一集合。無進捗検知はこの集合から `is_stall_exempt` を追加で除く」へ。
   - 書換え後、`grep -rn "同じ集合\|除外規則は 1 箇所\|_stalled_ids" karte/README.md karte/__init__.py karte/karte_record.py` が現行の判定と矛盾しないことを確認する。
4. `.ai/skills/issue-pipeline/SKILL.md`「②-c」の申し送り手順に、次を追加する：「`deferred` で申し送るときは、先に `decide` で `deferred_to` を記録し、`handoff-preview` を実行して**プレビュー全文（本文・宛先・警告）をチャットでオーナーへ提示し、明示承認を得てから** `handoff-post` を実行する（確認トークンは内容の同一性の担保で、承認の担保ではない）」。「実害の定義とエスカレーション」の2記述を書き換える。②-d の合流前確認に `handoff-recheck` を追加する。`decide`・`activate`・`ingest-review` と同じく**新 verb は主文脈専用**で、是正当事者ロールは実行できない。`.claude/skills/`・`.agents/skills/` 等の生成物や写しの同期は、`guidance_sync`・`asset_parity` の手順に従う（実装時に各 README で確認し、`python3 -m asset_parity check` を通す）。
5. Q1〜Q3 のオーナー決定と理由は本ファイル §1 と、#683 本体にも残す。

## 10. 試験（`gh` はモック・オフライン）
追加するテストと fixture は、`tests/unit/test_karte_finding_handoff_*.py` と `tests/fixtures/karte/` 配下。`gh` は `finding_handoff_github` の実行関数を差し替える。
- 転記ブロックの生成→解析→ハッシュの往復、対象フィールド以外の変更でハッシュが変わらないこと、対象フィールドの変更で変わること。
- `handoff-preview` が投稿も書込もしないこと、`handoff-post` が確認トークン無し・不一致で使用エラーになり**投稿しない**こと（確認なしの自動投稿をしない）。
- 投稿→読み戻し→照合→記録の一気通貫。照合失敗（本文改変・ブロック欠落・複数ブロック）で**検証済みを書かない**こと。投稿後の失敗でコメントを削除しないこと。
- 記録は verb だけが書く：レポートの `handoff_*` キーを `ingest-review`・`ingest-reviewer` が取り込みごと拒否すること。
- 全件再掲（内容が同じ）を跨いで記録が保持されること。内容が変わる再掲でハッシュ不一致により除外が外れること。
- **行き先の結び付き（F-809-01）**：検証後に `deferred_to` を別番号へ書き換えると計数へ戻ること。`--to` が `deferred_to` と異なる `handoff-post`・`handoff-preview` を拒否すること。`disposition` が `deferred` でない・未決定の finding、`harm: real` の finding、`status: resolved` の finding、プルリクエスト宛を拒否すること。
- **ロックと `gh`（F-809-02）**：`gh` を差し替えた関数がロック保持中に呼ばれないこと（`writer_lock` の保持を判定する関数で検査）。観測後・書込前に台帳の finding（`content_hash`・`deferred_to`）を書き換えると、`handoff-post`・`handoff-recheck` が記録を書かず `EXIT_ERROR` になること。`gh` のタイムアウト超過が検証失敗になり検証済みを書かないこと。
- **冪等性（F-809-03）**：投稿後に読み戻しを失敗させる `gh` モックで再実行しても、`gh` の投稿呼び出しが**1回に留まる**こと（既存ブロックの採用）。サーバ側作成後のタイムアウト→再実行で重複しないこと。台帳書込だけが失敗した後の再実行で採用されること。CRLF・末尾空白付きの本文でも照合できること。長さ上限超過・locked・認証失敗・レート制限が表のとおり扱われること。`@name` を含むプレビューに警告が出ること。
- **終了コード（F-809-07）**：`gh` 差替え関数に `CalledProcessError`・`TimeoutExpired`・不正 JSON・想定外のレスポンス形・`gh` 不在をそれぞれ起こさせ、`handoff-post`・`handoff-recheck` の終了コードが 4 で、標準エラーに traceback が無く、検証済みを書かないこと（recheck は `invalid`）。「観測後に finding が変わった」も終了コード 4。
- **行き先の正規化（F-809-08）**：別 repository の URL の行き先 `deferred_to` に対して自リポジトリの同番号へ `handoff-post` すると拒否されること。検証済みの finding の行き先を別 repository の URL へ書き換えると計数へ戻ること。`#N`・`N`・自リポジトリの URL が同じ正規形になること。
- **走査・投稿者・Issue 状態（F-809-09）**：2ページ目にだけ既存ブロックがある宛先で重複投稿しないこと（全ページ取得）。ページ取得失敗時に新規投稿しないこと。403 のレート制限（ヘッダ・本文）と権限不足を区別して案内すること。他者投稿のブロックを採用せず、recheck で `invalid` にすること。宛先 Issue の 404 で recheck が `invalid` にすること。**移転・改名（F-809-12）**：`gh` 差替え関数が、要求した対象と異なる repository の `html_url`・`repository_url`（または異なる `number`）を返すと recheck が `invalid` にすること（コメントの `issue_url` が異なる場合も同様）。
- **origin 非依存（F-809-11）**：origin を持たない一時ディレクトリで、検証済み記録つきの finding を含む karte の `status`・`render` が従来どおり実行でき、`git`・`gh` の差替え関数が**呼ばれない**こと。記録の repository と異なる URL の行き先で除外が外れること。origin が無い・github.com 以外・解析できない場合に `handoff-preview`・`handoff-post`・`handoff-recheck` が使用エラーになること（ssh 形式・`.git`・大文字小文字の解析を含む）。
- **前方非互換の記述（F-809-04）**：旧版相当の読み書き（`handoff_*` を知らない `parse`→`dumps`）で `handoff_*` が失われ、計数に戻ること（記述または試験で確認）。`handoff_*` キーの綴り違いが無視されて除外が効かないこと。
- 検証済み handoff を持つ `harm: none`・`deferred`・open の finding が、無進捗の計数と `render` の `★無進捗` から外れ、**verdict が `no-harm-only` のまま**であること。`harm: real` の `deferred`・`waived`・未検証・`invalid` の finding の計数が従来どおりであること（回帰）。
- §7 の復帰条件の各行（ハッシュ不一致・closed completed・closed not planned・コメント削除・コメント編集・`gh` 不可・復旧）。
- `status`・`render`・`check` がネットワークを呼ばないこと（`finding_handoff_github` を呼んだら失敗するモックで固定）。
- PR #627 の F-606-29・F-606-30 相当（`harm: none`・`deferred`・`rounds` が11ラウンド連続・申し送り先 open）のフィクスチャで、`escalate` の偽陽性が出ないこと。
- 両 gate（`.claude/hooks/agent-command-gate.sh`・`.codex/hooks/agent-command-gate.sh`）が新 verb を `issue-fixer`・`pr-reviewer` に対して deny すること。
- 既存の golden（K-01〜K-04）が**無変更で通る**こと（記録の無いカルテの出力が不変）。

## 11. AC との対応表
| AC（#683） | 設計の箇所 |
|---|---|
| verb 1回で転記ブロック生成→投稿→読み戻し→照合→記録。照合失敗時は検証済みを書かない | §3・§4（`handoff-post`・失敗時は書かない） |
| 検証済み記録は verb だけが書ける。レポートの handoff 系キーは取り込みごと拒否 | §5（`review_block` の拒否）・§4（記録は `handoff_store` 経由） |
| 検証済み handoff を持つ `harm: none`・`deferred` が無進捗の計数と `★無進捗` に出ない。verdict 不変 | §6 |
| ハッシュ不一致・closed・コメント削除/編集・`gh` 不可で計数へ戻る（各試験） | §7・§10 |
| 全件再掲を跨いで記録が保持される試験 | §5・§10 |
| 最終検証時に再検証でき、不一致や closed を出力で指摘 | §4（`handoff-recheck`）・§7・§9 |
| 試験は `gh` をモックしてオフライン。`status` はネットワークを呼ばない | §4（`finding_handoff_github` の境界）・§10 |
| README・docstring の 2026-09-07 記述の書換え・経緯の移設・覆す根拠と既知の限界 | §2・§9 |
| SKILL ②-c の更新。是正当事者ロールが verb を実行できないことの機械確認 | §4（両 gate の deny を試験で固定）・§9 |
| Q1〜Q3 のオーナー決定と理由の記録 | §1 |
| PR #627 の F-606-29・F-606-30 相当で `escalate` の偽陽性が出ない | §10 |
| `unittest discover` が green・`maintainability_lint check` が通る | §8（baseline 変更なし） |

## 12. 他 Issue との関係
- **#691 / #786**：自動 deferred は本 PR の検証済み handoff（`HandoffRecord`・`finding_handoff_verify`）を再利用する。本 PR に triager・policy を入れない。
- **#513**：停止要件の機械強制は別。本 PR の偽陽性の削減が #513 の全 deny の前提になる。
- **#614**：`check` の診断網羅要求は変更しない。述語の単一点（`finding_handoff_exemption`）を共有できる形にしてある。
- **#375・#496 系**：保護モードの `disposition`/`scope` の保持は変更しない。`decide` の記録は handoff を触らない。

## 13. 未確認事項（実装時に確認）
- `block_records.py`・`status_text.py` が100行以内に収まるか（収まらなければ分割し、baseline は更新しない）。
- `gh api` の出力（コメントの `body`・`html_url`、Issue の `state`・`state_reason`）の形と、`gh` の最小バージョン。
- 旧版（ロールバック先）の `block_records._finding_from_block` が未知の `handoff_*` を無視し、書き直すと失うこと（実コードで確認済みの前提。実装時に旧版相当の読み書きの試験で再確認する）。
- `handoff_cli` が `locked=False` の verb として `require_declared` を通り、書込だけを内部のロックで行う構成が `verb_boundary` の契約と整合するか（整合しない場合は PR7 の様式で選択肢と推奨を添えて報告する）。
- `.ai/skills/` と `.claude/skills/` の同期手順（`guidance_sync`・`asset_parity`）。
