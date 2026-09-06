# issue-implementer — 設計経緯・却下案・既知の限界（rationale・非規範）

> **これは規範ではない。** `.claude/agents/issue-implementer.md`（規範・正本）から Issue #372 で
> 移設した「設計判断の理由・却下案・既知の限界・過去インシデントの経緯・実測ログ」の保管先
> （PR8「消さない」＝削除ではなく移設）。**dispatch 時にロードされない**ので、行動を決める規範は
> すべて移設元に残っている。疑問が生じたときだけ参照する。
>
> - **移設元（規範・正本）**：`.claude/agents/issue-implementer.md`
> - **本文は移設元の文言を尊重して移した**（内容の変更・要約はしていない）。ただし `##` 見出しの
>   付与に加え、複数節をまとめる際・切り出した断片を単独の節として成立させる際に必要な最小限の
>   接続語・言い換えは補っている（見出しだけを付与した逐語移設ではない）。移設先で `##` 見出しを
>   付与し、どの節から来たかを併記している。
> - **相対参照は移設元の文脈を指す**：本文中の「後述」「上記」「下記」「本節」等は
>   移設元ファイル内の位置関係であって、本ファイル内の位置関係ではない。
> - 分離の方針・4ツリー波及方針は `.ai/rationale/README.md`。

## なぜ是正を兼用させないのか（移設元：「担当は「初回実装」だけ」節）

- 「是正の依頼が来たら着手せず STOP して報告する」の理由：

  本ロールにはカルテ（`tmp/_karte/issue-<N>.md`）の入力も `python3 -m karte` の実行権限も無く、
  前ラウンドの診断・失敗を引き継げないため、そのまま直すと「同じ直し方の連打」を検出できない。

- 型を分けている理由：`SubagentStop` のペイロードは `agent_type` しか持たず dispatch prompt を含まないため、
  1つの型を兼用すると**フックが初回実装か是正かを判別できない**。型が分かれていれば
  「`issue-fixer` は定義上つねにカルテを要する」となり、条件分岐なしの fail-close なゲートになる。

## `ISSUE_START_BINDING_V1` deny の切り分けと enforcement の実体（移設元：「dispatch 前提：`ISSUE_START_BINDING_V1` marker」節）

### Codex durable binding（Issue #452・2026-08-26、supervisor採用 2026-08-30）

Codex の message は暗号化されるため、Issue/round/repository/workspace/branch/OID/handoff/role/task key の
正本には使わない。当初は主文脈が ownership ledger へ prepare し、spawn hook が
task key で consume、全 tool hook が workspace/Git facts を再検証する方式を採用した。

PR #453 round 1 で、spawn payload `cwd` は main-thread の turn/session cwd で child workspace ではなく、
tool payload は `exec_command.workdir`、actual agent identity、spawn 成功を提供しないことが確定した。
task key を agent identity、turn cwd を effective workspace の代用にした当初方式は保証不能である。
`collaboration.spawn_agent` transportはunavailableのまま既存trusted issue-start hookでfail-closeする。
恒久経路はrepo supervisorがIssue専用worktreeで別Codex CLI processをOS sandbox下に起動する方式だけとした。
supervisorがPID/start tokenとJSONL threadをtrusted observationとして取得し、両方が揃ってから`running`へ
束縛する。inner processはhandoffまで、publishはhost gateへ分離する。判断・却下案・security trade-offの正本は
`docs/methods/codex-workspace-binding.md`。

F-452-19以後のsupervisor innerでは、Codex built-inのshell/unified exec/code modeを無効化し、task/attempt/fenceへ
束縛した単一MCP brokerだけをprocess入口にする。PATH denyやprompt規範ではabsolute launcher、copy、Node payloadを
閉じられないためである。brokerは任意argvを受けず、action別closed grammarから固定argvを組み立て、network/auth/
Codex installationをmountしない子bubblewrapで実行する。commit/push/PRは従来どおりhost publishの責務である。

`ISSUE_START_BINDING_MISSING_OR_DUPLICATE`（marker 欠如・複数行）や `ISSUE_START_BINDING_UNKNOWN_FIELD`
（field 過不足）等の deny を見た場合、本ファイルの実装ロジックではなく呼び出し元の dispatch prompt
（marker の付与漏れ・重複・field 不正）を疑う（enforcement の実体＝`issue_start/gate.py` の
`_claude_request`・`archive/issue-start-manifest-v1/managed-entrypoints-v1.json`（Issue #354 PR-4 で
archive 化・退役済み）の `claude` transport・設計根拠＝
`docs/tools/issue-start-and-branch-source.md`）。

## worktree 分離をなぜ dispatch 側でしか掛けられないのか（移設元：「dispatch 前提：`isolation: "worktree"`」節）

- **なぜ dispatch 側でしか掛けられないのか**：worktree 分離は本ロール自身では実現できない。
  `gitgate` に worktree を作る verb は無く（`new-branch` は検証済み OID を指定した `git switch -c`）、
  `agent-command-gate.sh` の層2 は `cd` を deny するため、仮に worktree を作れてもそこへ潜れない。
  分離を与えられるのは呼び出し元の dispatch だけで、その手段が Agent ツールの `isolation` パラメータ。
- **分離が効いているときの実際の姿**：cwd は `.claude/worktrees/agent-<id>/` の locked worktree
  （harness が Issue 番号ではなく agent id で命名する。`.worktrees/<name>/` ではない）。
  **呼び出し元のメインワークツリーは branch switch されない**ので、主文脈が並行して別の作業を
  していても衝突しない。`python3 -m unittest` もこの worktree を対象に走る。
- **分離は「書き込み範囲の制約」でもある**：worktree 外への Write はハーネスが機械的に拒否する。
  だからハンドオフの書き先は**自分の作業ツリー配下の相対パス**であり、メインワークツリーの
  絶対パスを渡される前提の手順は成立しない（後述「入力」「出力」＝Issue #323 で確定した契約）。
- **worktree の初期 HEAD は `origin/main` とは限らない**（harness が dispatch 時点のローカル状態から
  作るため）。ブランチは必ず `gitgate new-branch … --base-oid <fresh OID>` で切る（下記「責務境界」）。
  この verb は fresh fetch で OID を再検証し、食い違えば `BRANCH_BASE_OID_MISMATCH` で fail-close する。

## `handoff_path` を絶対パスではなく相対パスにした理由（移設元：「入力」節）

**なぜ絶対パスではなく相対パスなのか（Issue #323 で確定）**：本ロールは `isolation: "worktree"` 下で
動き、**ハーネスが作業ツリー外への Write を機械的に拒否する**。メインワークツリーの絶対パスへは
そもそも書けない。一方、相対パスなら**定義上つねに自分の作業ツリー配下**へ解決されるので、
「別のワークツリーを指すパス」という脅威が検査ではなく構造で消える。呼び出し元が結果を回収する
手段は**書けた絶対パスをチャットで返す**ことであって（後述「出力」）、書き先を絶対パスで
渡すことではない。この契約は isolated / 非 isolated のどちらの構成でも同じ文言のまま成立する。

## STOP 時も hand-off を書く理由

hand-off は dispatch が終了したことを呼び出し元が観測する signal である。STOP 時にチャットだけで報告すると、作業ツリーの回収・解放を開始できず手作業が必要になる。このため、`handoff_path` 自体が未提供で書込不能な着手前 STOP を除き、成功・失敗のどちらでも1件の hand-off を残す。

## allowlist の各項目がなぜその形なのか（移設元：「Bash 実行規律」節・Issue #373）

規範側には**操作可能な操作の一覧（＝この gated ロールの実質的な I/F）**だけを残し、
「なぜ deny なのか」という統制側の設計理由をここへ移した。理由を読まなくても、規範側の一覧だけで
正しいコマンドを書ける。

- **pytest が不可な理由**：任意 path/conftest/plugin を実行するため（第2次修正）。
- **`coverage run …` が deny な理由**：任意 Python 実行経路のため。
- **`python3 -m karte` が deny な理由**（Issue #308）：カルテは是正ラウンドの機構で、
  書き手は `issue-fixer` に一本化されている。
- **生 `git …` を deny して `gitgate` 経由にしている理由**：gitgate は固定テンプレートの git argv を
  `shell=False` で組み立てるため、`--receive-pack`/`--upload-pack`/`--output` 等の exec/write フラグが
  ユーザ入力から git に一切届かない。
