# Codex 実行経路の現行契約（`codex_worktree_exec`）

Issue #452 の Codex repo supervisor 方式は Issue #538 の PR-A で退役した。退役した実行契約・設計判断・却下案は
[`.ai/rationale/codex-supervisor-retirement-538.md`](../../.ai/rationale/codex-supervisor-retirement-538.md) へ移設した。
本書は Issue #538 の PR-B で導入した実行経路の現在の契約を記す。

## 結論

- **Codex は主文脈にしない。** 主文脈は Claude Code であり、Codex はサブ実行者として使う
  （オーナー決定・2026-09-22・Issue #538）。
- **Claude の `issue-implementer`／`issue-fixer` は、自分の linked worktree で Codex に編集とテスト実行だけを行わせることができる。**
  経路は `python3 -m codex_worktree_exec`（`codex exec -C <worktree>` の薄いラッパー）だけである（D12）。
- **Codex は commit・push・PR 作成をしない。** network は無効で、`.git` へは書けない。commit・push・PR 作成は
  呼び出し側の Claude ロールが既存の `agent-command-gate` の下で行う。
- **Codex 用フックは新設しない。** 権限境界は、版管理した permission profile（`.codex/config.toml`）、
  Claude 側 gate の起動形検査、ラッパーの起動前検査で担う。
- **Codex の `spawn_agent` で `issue-implementer`／`issue-fixer` を起動する経路は無い。**
  issue-start gate が常時 `ISSUE_START_TRANSPORT_UNAVAILABLE` で拒否する（後述）。

## 起動形

```
python3 -m codex_worktree_exec --role <自ロール> -C <自分の worktree ルート> \
  --prompt-file <依頼文> --output-file <最終応答> \
  --model <モデル> --reasoning-effort <low|medium|high|xhigh|max> [--timeout-seconds <1〜3600>]
```

（gated ロールは改行を使えないので、実際には1行で書く。）

- `--role` は呼び出し元自身の agent_type と一致しなければならない。`.claude/hooks/agent-command-gate.sh` が
  `issue-implementer`／`issue-fixer` にだけ、`--role` がちょうど1つでその値が自ロールである形を許可する。
- 依頼文と最終応答のファイルは worktree の `tmp/` 配下（gitignore 済み）に置く。依頼文は Write で書く。
- 終了コードは、検査不合格が `2`（stderr に `codex_worktree_exec: <識別子>: <詳細>` を1行出す）、timeout が `124`、
  それ以外は `codex exec` の終了コードをそのまま返す。
- 起動後、呼び出し側は Codex の変更を `python3 -m gitgate diff` と単体テストで自分で確かめてから commit する。
  依頼範囲外の変更が混じっていたら commit せず STOP して報告する。

### 検査の順序と識別子

すべての検査に通ったときだけ `codex exec` を起動する。どれか1つでも通らなければ起動しない。

| 順 | 検査 | 識別子 |
|---|---|---|
| 1 | 引数の形・ロール・モデル名・推論予算・timeout | `CODEX_EXEC_ARGUMENT_INVALID`／`CODEX_EXEC_ROLE_NOT_ALLOWED`／`CODEX_EXEC_MODEL_INVALID`／`CODEX_EXEC_EFFORT_INVALID`／`CODEX_EXEC_TIMEOUT_INVALID` |
| 2 | Codex の内側からの再帰起動（D6） | `CODEX_EXEC_NESTED` |
| 3 | `-C` の束縛（D5） | `CODEX_EXEC_WORKTREE_MISSING`／`CODEX_EXEC_CWD_NOT_IN_REPOSITORY`／`CODEX_EXEC_WORKTREE_CWD_MISMATCH`／`CODEX_EXEC_WORKTREE_UNREGISTERED`／`CODEX_EXEC_GIT_FAILED` |
| 4 | permission profile の base 一致（D1） | `CODEX_EXEC_PROFILE_MISSING`／`CODEX_EXEC_PROFILE_BASE_UNRESOLVED`／`CODEX_EXEC_PROFILE_DRIFT`／`CODEX_EXEC_PROFILE_UNDEFINED`／`CODEX_EXEC_GIT_FAILED` |
| 5 | project trust | `CODEX_EXEC_TRUST_UNRESOLVED`／`CODEX_EXEC_PROJECT_UNTRUSTED` |
| 6 | 依頼文・最終応答のファイル（D8） | `CODEX_EXEC_PROMPT_UNREADABLE`／`CODEX_EXEC_OUTPUT_INVALID` |
| 7 | 起動と timeout（D9） | `CODEX_EXEC_LAUNCH_FAILED`／`CODEX_EXEC_TIMEOUT` |

### Codex に渡す argv

```
codex exec -C <worktree> -c default_permissions="<role>" -m <model> \
  -c model_reasoning_effort="<effort>" --output-last-message <最終応答> -
```

依頼文は、固定の前置き（委譲しない・commit/push しない・範囲外を変更しない・最後に要約を返す）に本文を
続けて stdin で渡す。sandbox や承認を迂回する flag は渡さない。ラッパーはモデルと推論予算の既定値を持たない（D10）。

## permission profile

`.codex/config.toml` に `[permissions.issue-implementer]` と `[permissions.issue-fixer]` を同一内容で版管理する。
`pr-reviewer` の profile は置かない。

- `extends = ":workspace"`（workspace root＝`-C` の worktree へ書け、配下の `.codex/` と `.git/` は読取専用）。
- `[permissions.<role>.network]`：`enabled`・`allow_local_binding`・`dangerously_allow_all_unix_sockets`・
  `dangerously_allow_non_loopback_proxy` をすべて `false`。
- `[permissions.<role>.filesystem]`：`~/.codex/auth.json`・`~/.config/gh`・`~/.claude/.credentials.json`・`~/.ssh` を `deny`。

profile の構文は、パスを絶対パスか `~/` 始まりで書く。`unittest` の `tests/unit/test_codex_worktree_exec_assets.py` が、
両 profile の存在・同一性・network 無効・認証情報パスの deny を静的に検査する（実起動の代替ではない）。

## 「要設計」4項目の決定

1. **profile の選択経路**：project-local の `.codex/config.toml` に `[permissions.<role>]` を版管理し、ラッパーが
   `-c default_permissions="<role>"` で選ぶ。`--profile` が選ぶのは config profile で別概念である。
   task-private な `CODEX_HOME` へ profile を生成する方式（#452）は採らない。`-c` の dotted key で profile 本体を
   渡す方式は、ドットを含むパスの filesystem 規則を表現できないため採らない（実測⑧）。
2. **project trust**：未 trust の clone では Codex 自身が `default_permissions requires a [permissions] table` で
   exit 1 する（実測②・fail-close）。ラッパーも起動前に、main checkout の絶対パスについて `$CODEX_HOME/config.toml`
   （既定 `~/.codex/config.toml`）の `[projects."<path>"] trust_level = "trusted"` を確かめ、識別子付きで止める。
   main checkout の特定は `codex_hook_trust.repository.resolve_main_checkout` を再利用し、特定できなければ
   （渡されたパスへのフォールバック時を含む）判定不能として止める。
3. **フックの加算**：Codex 用フックは新設しない。`codex exec` では、trust 済みなら project の `.codex/hooks.json`
   （`agent-command-gate.sh`・`issue-start-gate.sh`）と user 層のフックが加算で走りうるが、権限境界をフックに
   依存させない。Codex が実行するコマンドは `agent_type` を持たないため、Codex 版 gate ではロール専用層の対象外となり、
   全ロール共通の merge／network・exec の deny だけが掛かる。
4. **権限の非対称**：Codex には profile の filesystem／network 規則で「編集とテスト実行だけ」をさせる
   （worktree 外・`.codex/`・git dir への書込みと network は不可）。merge と push の非対称を Codex に担わせない。
   commit・push・PR 作成は呼び出し側の Claude ロールが `agent-command-gate` の下で行う。`pr-reviewer` には
   ラッパーを許可せず、profile も置かない。

## 実起動 spike の実測（Codex 0.157.0）

検証専用の clone と使い捨ての linked worktree で、オーナー承認のもと主文脈が実測した。

1. trust 済みリポジトリの linked worktree では、worktree にだけある project-local `.codex/config.toml` の profile が読まれる。
2. 未 trust の通常 clone では `default_permissions requires a [permissions] table` で exit 1 する（fail-close）。
3. 未定義の profile 名は `refers to undefined profile` で exit 1 する（既定権限へのフォールバックは無い）。
4. read deny は profile を指定したときだけ効く。
5. worktree 外への書込み、`.codex/` への書込み、commit（git dir が読取専用）、network はいずれも拒否される。
6. `/tmp` への書込みは `:workspace` の既定で許可される（許容すると決定）。
7. `:workspace` の継承だけでは `~/.codex/auth.json`・`~/.config/gh/hosts.yml`・`~/.claude/.credentials.json` が読める
   （network 無効でも内容がモデル文脈へ流れる）。`"~/.codex/auth.json" = "deny"`・`"~/.config/gh" = "deny"`・
   `"~/.claude/.credentials.json" = "deny"` で塞がることを確認した。`~/.ssh` も deny に含めた（実測は TD で行う）。
8. `-c` の dotted key では、パスにドットを含む filesystem 規則を表現できない（このため profile は project config に置く）。

#565（素の `codex exec` が `AGENTS.md` の委譲指示に従って再委譲し停止する）は、spike の編集タスク1件では発生しなかった。
ラッパーの前置きで足りるかは、実起動検証の項目として TD に置く。

## 設計の暫定決定（D1〜D12）

audit 推奨・オーナー承認の暫定決定。番号は audit の番号をそのまま使う（D2・D3 は本 PR の実装に関わる決定として
引き継いでいないため本表に載せない）。

| ID | 暫定決定 | 覆る場合の影響範囲 |
|---|---|---|
| D1 | ラッパーは worktree の `.codex/config.toml` の blob OID を `origin/main:.codex/config.toml` と比べ、異なれば起動しない。比較先はローカルの `origin/main` ref で、ラッパーは fetch しない。 | 検査をやめると、呼び出し側が worktree 内で profile を緩めて起動できる。比較先を変えるなら `codex_worktree_exec/profile_pin.py`・同テスト・TD を改める。 |
| D4 | `--role` の値と呼び出し元 agent_type の一致を Claude 側 gate で検査する。ロールの allowlist は `GATED_ROLES` から `pr-reviewer` を除いて導出する（`codex_worktree_exec/roles.py` の `CODEX_EXEC_ROLES`。gate もここを読む）。 | 書込ロールを増減するときは `GATED_ROLES` と `.codex/config.toml` の profile を同時に変える。導出をやめると gate とラッパーの許可集合が別々に保守される。 |
| D5 | `-C` は登録済みの linked worktree で、かつ呼び出し元の cwd の toplevel と一致するものに限る。登録の確認は `gitgate.worktree.linked_worktree_paths` を再利用する。main checkout は指定できない。 | 条件を緩めると、別の dispatch の worktree や main checkout を Codex に書かせられる。 |
| D6 | Codex 版 gate の allowlist にラッパーを入れない。Codex の中からの再帰起動は `.codex/rules/default.rules`（`python3`／`python -m codex_worktree_exec` を forbidden）と、ラッパー自身の検知（自分が子へ渡す `CODEX_WORKTREE_EXEC_ACTIVE`、および Codex が sandbox 内コマンドへ付ける `CODEX_SANDBOX`・`CODEX_SANDBOX_NETWORK_DISABLED`）で止める。 | Codex から Claude ロールを経ずに Codex を起動できる経路を作るなら、Codex 版 gate と execpolicy の両方を設計し直す。 |
| D7 | 主文脈による直接起動は機械では止められない（gate のロール専用層は主文脈に掛からない）。「主文脈は実装を代行しない」を契約文に明記し、規律で守る。ラッパーは main checkout を `-C` に取らないため、主文脈が自分の checkout で起動しても止まる。 | 機械で止めるには、主文脈を識別するハーネス機能が要る（2026-07-11 のオーナー判断で gate 単独では不可と確定済み）。 |
| D8 | 依頼文はファイル引数、最終応答は `--output-last-message` の出力ファイルで受け渡す（層1が `<` `>` `|` を禁じるため）。 | stdin やパイプで渡す形に変えるなら gate の層1の例外設計が要る。 |
| D9 | ラッパーが timeout を持つ。既定 540 秒（Claude の Bash tool の上限 600 秒に収まる値）、上限 3600 秒。timeout ではプロセスグループへ SIGTERM、10 秒後に SIGKILL を送り、`CODEX_EXEC_TIMEOUT`（終了コード 124）で止める。540 秒を超える実行は Bash の `run_in_background` で起動する（実起動で確認する項目）。 | 既定値を変えると、Bash tool の timeout と食い違って結果を回収できなくなりうる。 |
| D10 | モデルと推論予算は呼び出し側が引数で指定し、ラッパーは既定値を持たない。レートリミットで止まったら同じ構成で再投入する（降格しない）。 | 既定値を持たせると、選定根拠（リスク信号表）を経ないモデルで走りうる。 |
| D11 | `issue-fixer` は Step 1 の診断（`karte render`→`karte append`）を済ませてからラッパーを起動する。Codex への依頼は Edit/Write と同じく診断後の編集に当たる。 | 前置しないと、診断を経ない是正が Codex 経由で入る。 |
| D12 | Codex にリポジトリを書かせる経路はこのラッパーだけとする。agy の `codex_*`（workspace-write）は使わない。 | 別経路を認めると、profile・`-C` 束縛・base 一致の検査を経ない書込みが生じる。 |

## 既知の限界

- `agent-command-gate` は静的なコマンド文字列検査であって sandbox ではない（Issue #129）。agent_type の詐称や
  ハーネス外の実行経路は防げない。
- D1 の比較先はローカルの `origin/main` ref であり、fetch が古ければ古い版と比べる。検査から Codex の起動までの間に
  profile を書き換える競合は防いでいない（呼び出し側は自分の worktree だけを持つ前提）。
- `/tmp` への書込みは許可される（実測⑥・許容）。
- 環境変数の秘匿値の扱いは Codex の既定の `shell_environment_policy` に依存し、spike では測っていない（TD の項目）。
- spike の linked worktree は main checkout の外に置いた。Claude の isolation worktree は main checkout 配下の
  `.claude/worktrees/agent-*` にあるため、この配置で worktree 側の profile が読まれることは実起動で確かめる（TD の項目）。

## `agent-command-gate.sh` の2ツリー乖離（事実の記録）

PR-B 着手時点（main `edbe35a`）で `.claude/hooks/agent-command-gate.sh` は約78.7K、`.codex/hooks/agent-command-gate.sh` は
約70K で、内容が乖離している。PR-B は D6 により Claude 側だけに `codex_worktree_exec` の許可を足したため、乖離は増える。
共通化は Issue #538 の範囲外である（SSoT／DRY の徹底機構の対象）。

## 実起動検証

検証設計は [`tests/designs/TD-codex-worktree-exec-538-001.md`](../../tests/designs/TD-codex-worktree-exec-538-001.md)。
TR とログは主文脈が検証専用環境で実起動して残す。`tests/unit/test_codex_worktree_exec_*.py` は model-free の事前検査であり、
実起動の代替にしない（#452 の evidence rule を踏襲する）。

## Codex `spawn_agent` の常時拒否

Codex の `spawn_agent` / `collaborationspawn_agent` で既知の `issue-implementer` / `issue-fixer` を
指定した dispatch は、issue-start gate が payload の詳細・cwd・ledger・GitHub API を読む前に
`ISSUE_START_TRANSPORT_UNAVAILABLE` で拒否する。malformed な payload でも理由は変わらない。
`issue_start/managed-entrypoints-v2.json` の `binding_transports` は `claude` だけを宣言し、
Codex の binding transport は置かない。

gate の判定順と Claude transport の marker／isolation 契約は
[`docs/tools/issue-start-and-branch-source.md`](../tools/issue-start-and-branch-source.md) を正とする。
Claude 経路の契約は supervisor の退役でも PR-B でも変更していない。

## 変更していないもの

- `codex-review`（別モデルファミリによる第二意見レビュー）と `.codex/mcp/claude_review/`。
- `.codex/hooks.json` に残る2つの PreToolUse hook（`agent-command-gate.sh`・`issue-start-gate.sh`）と、
  `.codex/hooks/agent-command-gate.sh` の判定内容。
- worktree 所有台帳（`issue_start/worktree_ledger.py`）と `durable_lock.py`。
- Claude の `issue-implementer`／`issue-fixer` の dispatch 契約（`ISSUE_START_BINDING_V1`／`ISSUE_FIX_BINDING_V1` marker と
  `isolation: "worktree"`）。

## 今後の予定

Codex を主文脈とする前提で書かれた資産（`.codex/agents/issue-implementer.toml`・`issue-fixer.toml`、
`.agents/skills/issue-pipeline` 等）の整理は Issue #603 で扱う。

## 記録の所在

| 記録 | 置き場 |
|---|---|
| 退役した supervisor 方式の実行契約・設計判断 | `.ai/rationale/codex-supervisor-retirement-538.md` |
| 主文脈を Claude Code とする決定の経緯 | `audit/2026-09-21-pipeline-redesign/README.md` |
| 実起動 spike の経緯・PR-B の設計確定事項 | Issue #538 本文・コメント |
| 実起動検証の設計 | `tests/designs/TD-codex-worktree-exec-538-001.md` |
| Issue #452 のテスト設計・テスト結果 | `archive/issue-452-codex-supervisor/` |
| Issue #452 のテストログ | `tests/logs/TD-issue-start-452-*` |
