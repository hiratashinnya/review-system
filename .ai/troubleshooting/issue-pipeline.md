# issue-pipeline — Claude worktree / handoff 回復手順

> **これは回復手順であり規範本文ではない。** 通常の dispatch 契約は [Claude wrapper](../../.claude/skills/issue-pipeline/SKILL.md) と共通本文を参照する。

## handoff の回収

dispatch の戻りが `HANDOFF: <絶対パス>` でも、isolated worktree の回収後はその絶対パスを直接 Read しない。次の順で回収済みファイルを読む。

1. `<main-worktree>/tmp/_worktree/ledger.json` を Read する。
2. `agent_type` と dispatch の `branch_name` が一致する最新エントリを特定する。
3. `collected_to` があれば `<main-worktree>/<collected_to>`（通常は `tmp/_handoff/collected/<entry-id>--<basename>`）を Read する。
4. `collected_to` が `null` で `status` が `stopped`/`stale` の場合は、主文脈で `python3 -m gitgate collect-worktree --entry <entry-id>` を実行してから 3 を再試行する。
5. `status: stop` の handoff は `stop_reason` とともにオーナーへ報告する。

`status` が `running` のままなら回収を強行しない。handoff 未作成、契約違反、クラッシュの可能性を確認し、下記の「保留」手順へ進む。`released` なのに `collected_to` が無い場合は worktree 実体と対応 PR の有無を read-only で確認して報告する。

## worktree 残留の回復

1. `ISSUE_START_WORKTREE_RESIDUE` の deny 文言にある entry を確認し、`python3 -m gitgate collect-worktree --entry <entry-id>` を実行する。
2. 台帳に紐づかない worktree が `ISSUE_START_WORKTREE_UNCLAIMED` で deny された場合は、対象 path を read-only で特定してから `python3 -m gitgate worktree-release <path> --force-uncollected --reason <text>` を実行する。
3. 回収不能な台帳 entry は、対象と理由を確認したうえで `python3 -m gitgate worktree-forget --entry <entry-id> --reason <text>` を使う。`ledger.json` を直接編集しない。

実装者／是正者の worktree は通常 `SubagentStop` が handoff 回収と解放を行う。手動解放は残留や回収失敗が観測された場合だけ行い、現在 live の dispatch が所有する worktree を対象にしない。

## 異常終了（レートリミット等）で `running` のまま残った worktree

レートリミット・セッション上限でサブエージェントが強制停止すると、停止フックが発火せず ledger entry が `running` のまま残り、worktree も対象ブランチを掴んだまま残る。この状態では後続 dispatch の `python3 -m gitgate adopt-branch` が必ず `BRANCH_ADOPT_LOCAL_EXISTS` で失敗する。

**通常は手作業が要らない。** レートリミット復帰の watcher が、解除を確認し**当該ペインが**アイドルと観測した地点で `python3 -m gitgate worktree-sweep-abandoned --no-live-dispatch --reason <text>` を1度だけ実行し、次のように処置する。

- 自分の handoff がある → 回収し、**回収後に作業ツリーが clean なときだけ**解放（`released`。git のロック等で削除だけが遅れる場合は `release-pending`）。**handoff の存在は clean 検査を免除しない。**
- handoff が無く、作業ツリーが clean かつ HEAD が `origin/<branch>` に含まれる → 失われる作業が無いので解放（`released`）。
- それ以外（回収後も残る未コミット/未追跡の変更、未 push のコミット、handoff が一意に決まらない、git が `locked` と報告） → **解放せず** `stale` へ落とすか `running` のまま残す。handoff を回収できていても dirty ならこちら（`kept-unsafe`）に落ちる。

**`--no-live-dispatch` の観測範囲は watcher に渡された単一 tmux ペインに限られる。** ペイン状態の判定は引数で渡された1ペインしか見ないのに対し、台帳（`tmp/_worktree/ledger.json`）はリポジトリ全体で共有される。したがってこの申告は「**そのペインからは**サブエージェントが実行中でない」以上のことを主張せず、別ペイン・別セッションで live な dispatch が動いていても真になりうる。**別ペイン・別セッションの live な dispatch を守るのは git の `locked` 判定だけ**であり、`git worktree list --porcelain` が `locked` と報告する worktree を掃引対象から外すことで担保する。ハーネスが live な agent worktree をロックしない構成ではこの保護が成立しないため、その環境では `CLAUDE_RL_SWEEP_WORKTREES=0` で掃引そのものを止める。

自動解放されなかったものは、従来どおり次の dispatch が `ISSUE_START_WORKTREE_RESIDUE` で deny し、その文言のコマンドで処置する。掃引の実行ログは `~/.claude/rate-limit-recovery/watcher.log`、判断の理由は ledger entry の `notes`（`worktree-sweep-abandoned:` 行）に残る。

**主文脈がこの verb を手で叩かない。** 「当該ペインからは live な dispatch が無い」という観測が成立するのは復帰イベントの地点だけで、それ以外から呼ぶと入れ子委譲中の正当な `running` を巻き込みうる（上記のとおり、その場合に残る歯止めは `locked` 判定だけである）。手作業で片付けるときは従来どおり `collect-worktree` / `worktree-forget` → `worktree-release` を使う。

## `adopt-branch` が `BRANCH_ADOPT_LOCAL_EXISTS` で失敗したとき

失敗文言に**誰がそのブランチを掴んでいるか**が出る。主体で処置が変わる。

- **primary checkout（メインワークツリー）** — レビュー担当がブランチを切り替えたまま戻していない状態。gitgate の worktree verb では解消しない。当該ワークツリーで `git switch <既定ブランチ>` を実行して戻す（主文脈が行う）。
- **agent worktree** — 台帳 entry が併記されていれば `python3 -m gitgate collect-worktree --entry <entry-id>`。回収不能なら `worktree-forget --entry <entry-id> --reason <text>` → `worktree-release <path> --force-uncollected --reason <text>`。
- **ローカル ref の tip が origin と違う** — 正体不明のローカル作業がある。内容を確認せずに消さない。

## hook と入れ子 dispatch の保留

`SubagentStart` は issue fixer のカルテ手順と実装者／是正者の worktree 所有を束縛し、`SubagentStop` は handoff の存在を確認してから台帳を進める。停止イベントだけで終了と判断しない。

実装者／是正者が内側の subagent へ委譲している間は、handoff が無い状態を `stopped`/`stale` に落とさず `running` のまま保留する。委譲が終わっても handoff が一度も作られず戻った場合は、ledger の entry を確認し、次の順で片付ける。

```text
python3 -m gitgate worktree-forget --entry <entry-id> --reason <text>
python3 -m gitgate worktree-release <path> --force-uncollected --reason <text>
```

台帳の直接編集や `git worktree remove` の直接実行はしない。判断不能、対象不明、回収後の PR 状態不明は STOP し、entry、path、handoff、PR URL、実行した read-only 確認を報告する。

## 旧 Claude wrapper から移設した観測・回収契約

dispatch の戻りは `HANDOFF: <実装者/是正者が実際に書けた絶対パス>` ＋1行要約。この絶対パスは isolated worktree 内部を指すが、**`SubagentStop` フックが同期的に `collect-worktree` を実行し、成功時は worktree ごと削除する**。happy path ではこの絶対パスは主文脈が読もうとする時点で既に存在しないため、**この絶対パスは Read しない**。

回収済みの実体を読む手順：

1. `<main-worktree>/tmp/_worktree/ledger.json`（worktree 所有台帳）を Read する。
2. `agent_type`（`issue-implementer` または `issue-fixer`）と `branch_name`（この dispatch に渡した値）が一致する**最新エントリ**を特定する。
3. そのエントリの `collected_to` を読む。値が入っていれば `<main-worktree>/<collected_to>`（`tmp/_handoff/collected/<entry-id>--<basename>`）を Read する。
4. `collected_to` が `null`（`status` が `stopped`/`stale` のまま自動回収が完了していない）なら、`python3 -m gitgate collect-worktree --entry <entry-id>` を主文脈が実行してから 3 を再試行する。`status` が `running` のままなら保留として扱い、契約違反・クラッシュの可能性を確認する。この状態で `collect-worktree` が `WORKTREE_LIVE` で拒否される場合は、`worktree-forget` → `worktree-release` の手順へ進む。`status` が既に `released` なのに `collected_to` が `null` のままなら、worktree の実体（残っていれば）と対応する PR の有無を主文脈が直接確認する。

実装者／是正者の worktree は `SubagentStop` フックが自動で回収・解放する（回収＝ハンドオフを `tmp/_handoff/collected/` へ退避してから解放する1操作。回収できなければ解放しない）。残留した場合（フック未発火・回収失敗）は次の dispatch が `ISSUE_START_WORKTREE_RESIDUE` で deny される。deny 文言のコマンドを実行して解消する。台帳に紐づかない worktree は `ISSUE_START_WORKTREE_UNCLAIMED` で deny されるため、対象 path を確認して `python3 -m gitgate worktree-release <path> --force-uncollected --reason <text>` を実行する。どうしても回収できないものは `python3 -m gitgate worktree-forget --entry <entry-id> --reason <text>` を使う。

恒常契約は各エージェントの `.md`/`.ai/agents/*.md` に常設し、フックは**機械的に拒否できる境界**だけに使う。

- `SubagentStart`（matcher `issue-fixer`）→ `.claude/hooks/subagent-karte-inject.sh`：カルテ手順を `additionalContext` として注入する。
- `SubagentStart`（matcher `issue-implementer|issue-fixer`）→ `.claude/hooks/subagent-worktree-bind.sh`：起動した dispatch の worktree を所有台帳へ束縛する。
- `SubagentStop`（matcher `issue-implementer|issue-fixer`）→ `.claude/hooks/subagent-stop-gate.sh`：`issue-fixer` の `karte check` 未通過を block し、通ったらその dispatch 自身の handoff が worktree にあるときだけ台帳を `running`→`stopped` へ進めて `collect-worktree` で回収・解放する。block したら回収へ進まない。フックは `git worktree remove` を直接呼ばず、実体を消してよいかの判断は `gitgate/worktree.py` に集約されている。

停止イベントは終了とは限らない。回収の起点にするのは「自分の handoff（`<agent_type>--issue-<N>…yaml`）が1件ある」という観測だけで、無ければ台帳を進めず `running` のまま保留する。内側の委譲中に停止イベントが繰り返し届くためである。保留を `stopped`/`stale` へ落とすと、それ自体が residue になり、同じ dispatch 自身の次の委譲まで `ISSUE_START_WORKTREE_RESIDUE` で deny される。

`issue-implementer` / `issue-fixer` が内側から subagent へ委譲すること（`*-author`→`reconciliation-validator`→`reconciliation` のノード著作チェーンを含む）は制限しない。入れ子委譲のあいだ停止イベントが繰り返され、委譲先の handoff が実装者／是正者の worktree の `tmp/_handoff/` に溜まる。実装者／是正者が handoff を一度も書かずに終了し ledger が `running` のまま残った場合は、`<main-worktree>/tmp/_worktree/ledger.json` の当該 entry を確認し、`python3 -m gitgate worktree-forget --entry <entry-id> --reason <text>` → `python3 -m gitgate worktree-release <path> --force-uncollected --reason <text>` で片付ける。
