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
