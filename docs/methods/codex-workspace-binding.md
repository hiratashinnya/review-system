# Codex 実行経路の現行契約（`codex_worktree_exec`）

Issue #452 の Codex repo supervisor 方式は Issue #538 の PR-A で退役した。退役した実行契約・設計判断・却下案は
[`.ai/rationale/codex-supervisor-retirement-538.md`](../../.ai/rationale/codex-supervisor-retirement-538.md) へ移設した。
本書は Issue #538 の PR-B で導入し、#371で工程ロールへ拡張した実行経路の現在の契約を記す。

## 結論

- **Codex は主文脈にしない。** 主文脈は Claude Code であり、Codex はサブ実行者として使う
  （オーナー決定・2026-09-22・Issue #538）。
- **Claude の工程ロールと `issue-fixer` は、自分の linked worktree で元ロールの権限を維持してCodexを起動できる。**
  read-only の `pr-reviewer` も、承認済みbindingを伴うレビューに限り同じexecutorを使える。経路は
  `python3 -m codex_worktree_exec`（`codex exec -C <worktree>` の薄いラッパー）だけである（D12）。
- **Codex は commit・push・PR 作成をしない。** network は無効で、`.git` へは書けない。commit・push・PR 作成は
  呼び出し側の Claude ロールが既存の `agent-command-gate` の下で行う。
- 権限境界は版管理した permission profile（`.codex/config.toml`）、両PFの既存command hook、
  Claude側gateの起動形検査、ラッパーの起動前検査で担う。#371は既存hookへ工程ロールを追加する。
- **Codex の `spawn_agent` で `issue-implementer`／`issue-fixer` を起動する経路は無い。**
  Codex は主文脈にせず、それらの Codex agent も置かない。Codex 側に issue-start hook は登録されていない（後述）。

## #371の工程入力・有効化境界

`issue-fixer`以外は `--binding-file <信頼callerのJSON>` が必須。初回調査・1aはraw Issue入力、
起動/省略理由、Issue/run/target、bytes digest、HEADのsnapshot OIDを束縛する。
後続工程はcommit済みartifactのpath/digestと、producer/phase/Issue/run/target/input digest/
source snapshot OID/参照のexpectedを信頼callerから受け取る。artifactは正規配置とsource snapshotの
到達可能性も確認し、実装者は承認済み単一work unitを要求する。期待値を入力から補完しない。
相談は元role/run/入力参照、model、回数/token/費用予算へ束縛し、完全回答とtrusted使用量だけをcaptureする。
回答は採否未決で元担当へ返し、レビュー・owner承認・STOPを解除しない。

Claude native dispatchは全工程でphase binding/承認receiptを要求する。read-onlyのClaude側dispatchは
worktree所有台帳を作らない。Codex executorへの委譲では引き続き呼出元のlinked worktree確認が必要。
新工程のmanifestはavailableとし、必須binding/承認検査を通る正規入口だけを使用する。
owner決定 `.ai/feedback/ledger/FBK-20261017-工程別worktreeへ同一branchを継承する.toml` に従い、
著作ロールは同一branchのremote exact OIDを各role専用worktreeへ継承する。
使用中branch拒否を維持し、同一worktree所有権移管や旧implementer初回入口による迂回は行わない。
origin/mainとのprofile pinは緩めない。未merge profileの実起動拒否は想定された保護であり、
モデル非呼出しテストの成功で実dispatch成功を代用しない。低・中・高リスク経路と相談の実測は
[`issue_envelope/verify/designs/post-merge-verification-371.md`](../../issue_envelope/verify/designs/post-merge-verification-371.md)
の手順および [Issue #652](https://github.com/hiratashinnya/review-system/issues/652) で追跡する。

2026-10-16時点のunavailableは同一worktree/adopt衝突の判断未決による停止だった。
2026-10-17にownerがrole専用worktree方式を選択したため、この停止は現行のavailability条件から除いた。
ロール別製品実dispatchの証拠は引き続き未実測であり、#652で検証する。

## 起動形

```
python3 -m codex_worktree_exec --role <自ロール> -C <自分の worktree ルート> \
  --prompt-file <依頼文> --output-file <最終応答> \
  --model <モデル> --reasoning-effort <low|medium|high|xhigh|max> [--timeout-seconds <1〜3600>]
```

（gated ロールは改行を使えないので、実際には1行で書く。）

- `--role` は呼び出し元自身の agent_type と一致しなければならない。`.claude/hooks/agent-command-gate.sh` が
  工程ロールと `issue-fixer` に、`--role` がちょうど1つでその値が自ロールである形だけを許可する。
- 依頼文と最終応答のファイルは worktree の `tmp/` 配下（gitignore 済み）に置く。依頼文は Write で書く。
  相対パスは呼び出し元 cwd を起点とし、親 symlink を解決した実パスが検査済み worktree の `tmp/` 内に
  あることを起動前に確認する。境界外の絶対パス・`../`・symlink は拒否する。`tmp/` 自体が境界外へ
  symlink で移されている場合も拒否する。
- 終了コードは、通常ロールでは検査不合格が `2`（stderr に `codex_worktree_exec: <識別子>: <詳細>` を出す）、
  timeout が `124`、起動後は `codex exec` の終了コードをそのまま返す。`pr-reviewer` はCodex出力を透過せず、
  Codex異常終了または取り込み失敗を `2`、Codex成功かつ取り込み成功を `0` で返す。
  `pr-reviewer` のIssueは承認済み `expected.issue` と起動時および取り込み直前の進行ポインタを照合し、
  roundも起動時から変化していないことを要求する。bindingに `expected.issue` がない場合は Codex 起動前に
  `CODEX_EXEC_BINDING_INVALID` または `CODEX_REVIEW_INGEST_FAILED` で停止する。
  reviewer で Codex が異常終了した場合は、ANSI制御文字を除去した stderr の末尾を複数行（最大6行・1000文字）返す。
- 取り込み失敗で `karte` が拒否理由を出した場合、拒否見出しそのものと、その直後に連続する箇条書きを返す（間に別の行が挟まるとそこで打ち切る）。全体が8行・1000文字以内なら省略せず、上限を超える場合は省略表示を含めて合計8行・1000文字以内にする。`N` は省略された行数とし、見出し1行または箇条書き1行が長い場合は「…」で切って返す。拒否見出しがない失敗では、空でない stderr/stdout の最後の行を返す。
- 取り込みの timeout（60秒）は台帳・期待値の状態が不明な取り込み失敗として `CODEX_REVIEW_INGEST_FAILED`（終了コード `2`）を返すため、`karte status` と `tmp/_karte/active.json` を確認してから再実行する。成功時の karte の非警告出力は wrapper の stderr にそのまま中継し、呼び出し側への戻り値は従来どおり「取り込み済み」の1行＋警告行とする。
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
| 8 | `pr-reviewer` の Codex 実行・外側取り込み（Issue #375） | `CODEX_REVIEW_CODEX_FAILED`／`CODEX_REVIEW_INGEST_FAILED` |
| 9 | 承認済み artifact binding | `CODEX_EXEC_BINDING_MISSING`／`CODEX_EXEC_BINDING_INVALID` |

### Codex に渡す argv

```
codex exec -C <worktree> -c default_permissions="<profile>" -m <model> \
  -c shell_environment_policy.inherit="core" \
  -c model_reasoning_effort="<effort>" --output-last-message <最終応答> -
```

依頼文は、固定の前置き（委譲しない・commit/push しない・範囲外を変更しない）に本文を続けて stdin で渡す。
通常ロールには最後に要約を求め、`pr-reviewer` には構造化レポート本文だけを最終応答にするよう求める。
sandbox や承認を迂回する flag は渡さない。ラッパーはモデルと推論予算の既定値を持たない（D10）。

### Codex に渡す環境

呼び出し元の環境は、ラッパーの許可リストと Codex のシェルの `core` 集合の2段で絞る（F-538-32）。
ラッパーは `codex_worktree_exec/child_environment.py` の `CODEX_CHILD_ENVIRONMENT_ALLOWLIST` に定義した
次の名前だけを `codex exec` のプロセスへ継承する。

- 起動・ユーザー情報：`PATH`・`HOME`・`USER`・`LOGNAME`・`SHELL`。
- ロケール・端末・時刻：`LANG`・`LC_ALL`・`LC_CTYPE`・`TERM`・`TZ`。
- 一時ファイル：`TMPDIR`・`TEMP`・`TMP`。
- Codex の設定・認証と標準の設定・キャッシュ・データ配置：`CODEX_HOME`・`XDG_CONFIG_HOME`・
  `XDG_CACHE_HOME`・`XDG_DATA_HOME`。Codex 本体の認証は `CODEX_HOME` 配下の `auth.json` を使う
  （未指定時は `~/.codex`）。

許可リスト外の変数は名前や値によらず渡さない。`TOKEN`・`KEY`・`SECRET`・`PASSWORD`・`CREDENTIAL` を
名前に含む変数や、`CLAUDE_*`・`ANTHROPIC_*`・`GH_*`・`GITHUB_*`・`OPENAI_*` も継承しない。
ラッパー自身の再帰検知の標識 `CODEX_WORKTREE_EXEC_ACTIVE=1` は追加して子の Codex へ渡す。
許可リスト外の変数を渡すには本契約と許可リスト・対応テストの変更が必要であり、呼び出しごとの追加指定は設けない。

さらに `codex exec` の引数として `-c shell_environment_policy.inherit="core"` を必ず渡し、Codex のシェルへ
継承する環境を `core` 集合に絞る。既定の除外は有効のままとし、ラッパーは除外の解除や追加変数の設定を行わない。
モデルを呼ばない対応テストは許可・除外・標識と argv を検査し、実際のシェル環境は TD の手順 7 で再検証する。

## permission profile

`.codex/config.toml` に著作ロール（ac-designer/change-planner/test-writer/issue-implementer）とissue-fixerの編集profile、
調査・plan-reviewer・pr-reviewer・adviserのread-only profileを版管理する。
config の最初の有効設定はトップレベルの `default_permissions = "secure-default"` とする（F-538-24）。
`[permissions.secure-default]` は `:workspace` を継承し、role profile と同じ network deny と認証情報パス deny を持つ。
これにより project config を読む未指定の直接起動も、編集可能な workspace 権限を保ちながら認証情報を読めない。
`codex_worktree_exec` は role に対応する profile を明示選択するため、この既定値を使わない。`finding-triager` は既存 `adviser` の read-only profile を共有し、pin に加え権限内容を検査する。
`secure-default` は起動時の既定でありロールではない。`CODEX_EXEC_ROLES` や wrapper の `--role` 許可集合には含めない。

Codex 起動の実効権限は sandbox 指定と project config の組合せで決まる。`--sandbox read-only` や `codex-review`
のような read-only 起動では、その読取専用境界を維持し、`secure-default` の `:workspace` 継承で writable にしない。
config の適用範囲は Codex が読み込む trusted project-local `.codex/config.toml` に限る。未 trust の project、別 repository
からの起動、global config、CLI override、変更された `CODEX_HOME` には本設定の適用を保証しない。
直接起動の実測は対象 project と trust 状態、Codex version、sandbox 指定を記録して行う。

- 著作/fixerは `extends = ":workspace"`（`-C` の worktreeへ書け、配下の `.codex/` と `.git/` は読取専用）。
- 調査・レビュー・adviserは `extends = ":read-only"` とし、編集権限を与えない。
- `[permissions.secure-default.network]` と `[permissions.<role>.network]`：`enabled`・`allow_local_binding`・`dangerously_allow_all_unix_sockets`・
  `dangerously_allow_non_loopback_proxy` をすべて `false`。
- `[permissions.secure-default.filesystem]` と `[permissions.<role>.filesystem]`：`~/.codex/auth.json`・`~/.config/gh`・`~/.claude/.credentials.json`・`~/.ssh` を `deny`。

profile の構文は、パスを絶対パスか `~/` 始まりで書く。`unittest` の `tests/unit/test_codex_worktree_exec_assets.py` が、
先頭の既定設定・secure-default とロール別profile・著作profileの同一性・network無効・認証情報パスのdeny を静的に検査する
（未指定・`--sandbox read-only` の実起動成功の代替ではない）。

## 「要設計」4項目の決定

1. **profile の選択経路**：project-local の `.codex/config.toml` に profile を版管理し、ラッパーが
   role に対応する `-c default_permissions="<profile>"` で選ぶ。`finding-triager` の対応先は `adviser` で、固定済み read-only 権限の検査を必須とする。`--profile` が選ぶのは config profile で別概念である。
   task-private な `CODEX_HOME` へ profile を生成する方式（#452）は採らない。`-c` の dotted key で profile 本体を
   渡す方式は、ドットを含むパスの filesystem 規則を表現できないため採らない（実測⑧）。
2. **project trust**：未 trust の clone では Codex 自身が `default_permissions requires a [permissions] table` で
   exit 1 する（実測②・fail-close）。ラッパーも起動前に、main checkout の絶対パスについて `$CODEX_HOME/config.toml`
   （既定 `~/.codex/config.toml`）の `[projects."<path>"] trust_level = "trusted"` を確かめ、識別子付きで止める。
   main checkout の特定は `codex_hook_trust.repository.resolve_main_checkout` を再利用し、特定できなければ
   （渡されたパスへのフォールバック時を含む）判定不能として止める。
3. **フックの加算**：Codex 用フックは新設しない。`codex exec` では、trust 済みなら project の `.codex/hooks.json`
   （Bash の `agent-command-gate.sh` と `adr-notify.sh`）と user 層のフックが加算で走りうるが、権限境界をフックに
   依存させない。Codex が実行するコマンドは `agent_type` を持たないため、Codex 版 gate ではロール専用層の対象外となり、
   全ロール共通の merge／network・exec の deny だけが掛かる。
4. **権限の非対称**：著作/fixerの Codex には profile の filesystem／network 規則で「編集とテスト実行だけ」をさせる
   （worktree 外・`.codex/`・git dir への書込みと network は不可）。read-only の `pr-reviewer` はレビューだけを行い、
   `--output-last-message` の保存後に外側の `codex_worktree_exec` が既存 `ingest-reviewer` を実行する（Issue #375 案B）。
   この経路も linked worktree、D5、read-only profile、network無効、artifact binding の検査を維持する。
   wrapper は binding の `expected`（run_id・target_key・snapshot_oid）と検証済み `artifact_digest` から review handoff の
   共通 envelope ヘッダを作り、`ingest-reviewer` が主文脈の `karte activate` で記録した期待値との一致を要求する
   （別 run・古い snapshot の取り込みを拒否する。Issue #375）。`ingest-reviewer` が取り込み済みだが再掲漏れで未完了
   （終了コード 5）を返した場合、wrapper は取り込み失敗（`CODEX_REVIEW_INGEST_FAILED`・終了コード 2）と区別して
   `CODEX_REVIEW_INGEST_INCOMPLETE`（終了コード 5）を返す。台帳の round は記録済み・期待値は消費済みなので、同じ
   handoff を再取り込みせず、主文脈が `karte activate` で期待値を記録し直して再レビューする。
   Codex 本体に karte の書込権限は与えず、`.codex/hooks/agent-command-gate.sh` の pr-reviewer×karte 拒否も変えない。
   merge・push・PR 作成は引き続き呼び出し側の Claude ロールが `agent-command-gate` の下で行う。

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
9. profile を定義してトップレベルの `default_permissions` を省略すると、Codex 0.157.0 の未指定起動は
   `config defines [permissions] profiles but does not set default_permissions` で失敗する。
   `--sandbox read-only` 併用時は `failed to load workspace requirements` と報告される（F-538-24 の実測）。

#565（素の `codex exec` が `AGENTS.md` の委譲指示に従って再委譲し停止する）は、spike の編集タスク1件では発生しなかった。
ラッパーの前置きで足りるかは、実起動検証の項目として TD に置く。

## 設計の暫定決定（D1〜D12）

audit 推奨・オーナー承認の暫定決定。番号は audit の番号をそのまま使う（D2・D3 は本 PR の実装に関わる決定として
引き継いでいないため本表に載せない）。

| ID | 暫定決定 | 覆る場合の影響範囲 |
|---|---|---|
| D1 | ラッパーは worktree の `.codex/config.toml` の blob OID を `origin/main:.codex/config.toml` と比べ、異なれば起動しない。比較先はローカルの `origin/main` ref で、ラッパーは fetch しない。 | 検査をやめると、呼び出し側が worktree 内で profile を緩めて起動できる。比較先を変えるなら `codex_worktree_exec/profile_pin.py`・同テスト・TD を改める。 |
| D4 | `--role` の値と呼び出し元 agent_type の一致を Claude 側 gate で検査する。ロールの allowlist は `CODEX_EXEC_ROLES = GATED_ROLES`（`codex_worktree_exec/roles.py`）から導出し、`pr-reviewer` を含む。 | `GATED_ROLES` を変えるとCodexラッパーの許可集合も追随する。導出をやめるとgateとラッパーの許可集合が別々に保守される。 |
| D5 | `-C` は登録済みの linked worktree で、かつ呼び出し元の cwd の toplevel と一致するものに限る。登録の確認は `gitgate.worktree.linked_worktree_paths` を再利用する。main checkout は指定できない。 | 条件を緩めると、別の dispatch の worktree や main checkout を Codex に書かせられる。 |
| D6 | Codex 版 gate の allowlist にラッパーを入れない。Codex の中からの再帰起動は `.codex/rules/default.rules`（`python3`／`python -m codex_worktree_exec` を forbidden）と、ラッパー自身の検知（自分が子へ渡す `CODEX_WORKTREE_EXEC_ACTIVE`、および Codex が sandbox 内コマンドへ付ける `CODEX_SANDBOX`・`CODEX_SANDBOX_NETWORK_DISABLED`）で止める。 | Codex から Claude ロールを経ずに Codex を起動できる経路を作るなら、Codex 版 gate と execpolicy の両方を設計し直す。 |
| D7 | 主文脈による直接起動は機械では止められない（gate のロール専用層は主文脈に掛からない）。「主文脈は実装を代行しない」を契約文に明記し、規律で守る。ラッパーは main checkout を `-C` に取らないため、主文脈が自分の checkout で起動しても止まる。 | 機械で止めるには、主文脈を識別するハーネス機能が要る（2026-07-11 のオーナー判断で gate 単独では不可と確定済み）。 |
| D8 | 依頼文はファイル引数、最終応答は `--output-last-message` の出力ファイルで受け渡す（層1が `<` `>` `|` を禁じるため）。両ファイルの実パスは検査済み worktree の `tmp/` 内に限り、境界外は `CODEX_EXEC_PROMPT_UNREADABLE`／`CODEX_EXEC_OUTPUT_INVALID` で起動前に拒否する。 | stdin やパイプで渡す形に変えるなら gate の層1の例外設計が要る。 |
| D9 | ラッパーが timeout を持つ。既定 540 秒（Claude の Bash tool の上限 600 秒に収まる値）、上限 3600 秒。timeout ではプロセスグループへ SIGTERM、10 秒の猶予後に残存グループへ SIGKILL を送り、`CODEX_EXEC_TIMEOUT`（終了コード 124）で止める。leader が先に正常終了しても、残る子は同じ対象とする。540 秒を超える実行は Bash の `run_in_background` で起動する（実起動で確認する項目）。 | 既定値を変えると、Bash tool の timeout と食い違って結果を回収できなくなりうる。 |
| D10 | モデルと推論予算は呼び出し側が引数で指定し、ラッパーは既定値を持たない。レートリミットで止まったら同じ構成で再投入する（降格しない）。 | 既定値を持たせると、選定根拠（リスク信号表）を経ないモデルで走りうる。 |
| D11 | `issue-fixer` は Step 1 の診断（`karte render`→`karte append`）を済ませてからラッパーを起動する。Codex への依頼は Edit/Write と同じく診断後の編集に当たる。 | 前置しないと、診断を経ない是正が Codex 経由で入る。 |
| D12 | Codex にリポジトリを書かせる経路はこのラッパーだけとする。agy の `codex_*`（workspace-write）は使わない。 | 別経路を認めると、profile・`-C` 束縛・base 一致の検査を経ない書込みが生じる。 |

## 既知の限界

- `agent-command-gate` は静的なコマンド文字列検査であって sandbox ではない（Issue #129）。agent_type の詐称や
  ハーネス外の実行経路は防げない。
- F-538-25 の残る限界として、依頼文・最終応答のパス検査（`prompt_files.py`）は、検査後に `tmp/` 内の
  親ディレクトリや対象を差し替える競合（TOCTOU）を防がない。これは意図的な回避であり、善意のエージェントの
  自然な逸脱を封鎖するゲートの脅威モデルの範囲外で、Issue #129 の限界として受容する。出力先は Codex 本体が
  後で書くため、ラッパー側では完全には閉じられない。2026-10-13 のオーナーの明示判断で受容した限界である
  （`waived_by: オーナー`）。
- D1 の比較先はローカルの `origin/main` ref であり、fetch が古ければ古い版と比べる。検査から Codex の起動までの間に
  profile を書き換える競合は防いでいない（呼び出し側は自分の worktree だけを持つ前提）。
- `/tmp` への書込みは許可される（実測⑥・許容）。
- F-538-30：ラッパーを通さない起動（`codex exec` の直接起動・`codex-review`・対話利用）にも、
  trusted project config が読み込まれる場合は `secure-default` が適用され、認証情報パスを deny する。
  この設定は #630 で導入した。D12 は「ラッパーが Codex にリポジトリを書かせる唯一の**許可された**経路」という
  規律であり、ラッパーを通さない起動そのものを拒否するものではない。`secure-default` は project-local config が
  適用される起動の保護であり、env に含まれた秘密、別パスの認証情報、未 trust project、他リポジトリ起動を包括しない。
- #630 の実起動確認（2026-11-03、Codex 0.166.0、`issue/630-secure-default` checkout）では、直接 exec と対話 UI の
  起動・応答、read-only の書込拒否、workspace-write の一時領域書込、`.codex/`・`.git/` の書込拒否、network socket
  拒否を確認した。コマンドと未検証経路は下表のとおり。これはローカル実行環境での結果であり、未確認経路を製品 PASS とみなさない。

| 経路 / コマンド | 条件・結果 |
|---|---|
| `codex exec --ephemeral -C . "Reply exactly: started"` | 既定 sandbox は `workspace-write [workdir, /tmp, $TMPDIR]`、model `gpt-6-luna`。exit 0、`started`。project の trust 状態を `codex_hook_trust` では独立確認できなかった。 |
| `codex exec --ephemeral --sandbox read-only -C . "Reply exactly: started"` | Codex 0.166.0 が起動・応答。read-only の一時ファイル作成 probe は `DENIED OSError`。 |
| trusted main checkout での実認証 smoke | `rtk codex exec --ephemeral --sandbox read-only -C . -m gpt-6-luna 'Reply exactly: secure-default-auth-ok'` は Codex 0.166.0、default `secure-default` に read-only sandbox 指定を重ねて exit 0、応答は `secure-default-auth-ok` と一致。実ユーザーのsecretは表示・複製していない。これは Codex model 認証が secure-default 下で動く証拠であり、app-server / `hooks/list` が実ユーザー HOME で成功した証拠ではない。 |
| `issue-implementer` profile の直接起動 smoke | trusted main checkout で `rtk codex exec --ephemeral -C . -c 'default_permissions="issue-implementer"' -m gpt-6-luna '<smoke request>'` を実行し、exit 0・workspace-write profile で応答。これは profile の直接指定確認であり、wrapper role の起動成功を示さない。 |
| `codex --no-alt-screen -C .`（TTY） | Codex 0.166.0 の対話 UI 起動後、`Reply exactly: started` に応答し、Ctrl-C で終了。 |
| default workspace-write sandbox の一時 probe | `./tmp` と repository root での一時 file 作成・即時削除は `CREATED`、`.codex/` と `.git/` は `DENIED OSError`、`1.1.1.1:443` socket は `BLOCKED PermissionError`。 |
| `~/.codex/auth.json`・`~/.config/gh`・`~/.claude/.credentials.json` の open probe | Codex 0.166.0、`codex exec --ephemeral -C .` の既定 `workspace-write` sandbox 内で `os.open(O_RDONLY)`（gh は `O_RDONLY|O_DIRECTORY`）を行い、FD を直ちに閉じた。内容の read・表示・収集なし。既存する3対象すべて `DENIED PermissionError`、Codex exec exit 0。sandbox deny を実測。 |
| 既定 workspace-write sandbox 内 `~/.ssh` open probe | 実 HOME で path 不存在。存在しないため deny の実効確認にはならない。path を含む probe command は `agent-command-gate` が文字列 `ssh` を全 role に対する拒否対象として実行前に止めた。gate の拒否を sandbox deny と扱わず、この実 HOME path の workspace-write probe は**未検証**。secure-default profile の隔離 HOME dummy target probe は別行に記録。 |
| `codex sandbox -P secure-default` credential deny probe | 隔離 HOME/CODEX_HOME 内に4つの明示的な dummy target files（`auth.json`、gh credentials、Claude credentials、`.ssh` target）を作成し、Codex 0.166.0 の `codex sandbox -P secure-default` から各ファイルを read-only open。内容は読まず、全4件 `EACCES`。外側 sandbox 内の最初の実行は app-server socket directory mode error で止まったが、外側を `require_escalated` で起動した再実行では内側 Codex の secure-default profile が有効のまま全4件を拒否。dummy target に対する profile deny の実測であり、実 credential の拒否を意味しない。 |
| `python3 -m codex_hook_trust check --repo .` / app-server `initialize` → `hooks/list` | 実 `~/.codex` では前者 exit 2、`app-server closed stdout before replying`。stderr は `failed to initialize sqlite state runtime under ~/.codex`。直接 JSON-RPC でも initialize 応答前に stdout が閉じ、exit 1。`codex app-server --print-startup-config` は exit 0。隔離 HOME/CODEX_HOME（実認証情報なし）に dummy `auth.json` と trusted project config を置いた検証では initialize と `hooks/list` が成功し hook 2件を返したが、両方 `untrusted`、`codex_hook_trust` は exit 1。これは dummy auth のみで、実認証を検証していない。実ユーザー環境の `codex login status` は `Logged in using ChatGPT`。実ユーザー認証を隔離 HOME へ symlink する案は auto-review が情報漏えいリスクを理由に拒否したため試していない。よって実ユーザー認証下の app-server / hooks trust は**未検証**。 |
| 隔離 HOME/CODEX_HOME での通常 exec と codex-review stdin | 隔離 HOME に `.codex/config.toml` と trusted project 設定を置いたが、認証は dummy `auth.json` のみ。`codex exec --ephemeral --sandbox read-only -C <project> -m gpt-6-luna "<ordinary user request>"` と、codex-review の実 stdin 形式 `codex exec --ephemeral -m gpt-6-luna --sandbox read-only - < prompt.txt` はどちらも通常の user request で exit 1。モデル応答はなく、`network request failed` / `plan type is required for chatgpt authentication`。秘密値は出力していない。これは dummy auth 条件であり、実ユーザー認証下の通常 exec・codex-review は**未検証**。 |
| `codex-review` 実レビュー | `codex exec --sandbox read-only review --base origin/main -m gpt-6-luna --ephemeral` は Codex 由来の独立read-only reviewとして exit 0、明確な指摘なし。ただし `.claude/skills/codex-review/SKILL.md` の stdin entry `codex exec -m gpt-6-luna --sandbox read-only - < prompt.txt` は exit 1。Codex 0.166.0 が `failed to initialize in-process app-server client: Read-only file system` を返した。`--ephemeral` を付けても同じで、この skill entry は**未検証／実行不能**。実ユーザー認証に基づくskill entry実行も未検証。 |
| wrapper role 実起動 / origin/main pin | 一時 linked worktree で `rtk python3 -m codex_worktree_exec --role issue-implementer -C . --prompt-file tmp/issue630-role-smoke.prompt --output-file tmp/issue630-role-smoke.out --model gpt-6-luna --reasoning-effort high` を実行。現在の agent sandbox が入れ子起動を止め、exit 2 `CODEX_EXEC_NESTED: CODEX_SANDBOX_NETWORK_DISABLED` で pin 検査前に終了。wrapper を sandbox 内からさらに起動する経路は**未検証**。同 linked worktree の実 blob は `origin/main:.codex/config.toml=82bd8263…`、worktree config=`90e6fd36…` と異なるため、D1 pin が拒否する条件を確認。`tests.unit.test_codex_worktree_exec_profile` と `tests.unit.test_codex_worktree_exec_cli` は 10 tests / 5.465s / OK で profile drift 拒否を検証。 |

単体テスト結果（2026-11-03）：root checkout で `python3 -m unittest discover -s tests/unit` は 2509 tests / 998.477s / exit 1。5 errors は、sandbox が `.codex/` を read-only にし、既存 `test_codex_agent_command_gate.py` fixture が一時 hook file を作れないためだった。同moduleを `/tmp` 上の writable なコピーで実行すると 74 tests / 250.038s / OK。さらに `/tmp/review-system-issue630-discovery` に local clone を作り、正規 origin URL と origin/main=29b8d47 を設定して full discovery を再実行し、2509 tests / 1279.270s / OK。最初の clone 実行で出た27 failures は clone origin URL がローカルパスで dispatch target repo を解決できなかったためで、正規 GitHub URL へ修正した再実行では解消した。clone 実行では fetch/push を行っていない。`python3 -m asset_parity check` は 49 assets / 0 MISSING / 18 heuristic staleness flags、exit 0。`python3 -m maintainability_lint check` は violations 0 / accepted debt 77、exit 0。

上記の未検証事項は acceptance criterion 完了の証拠ではない。特に実ユーザー認証下の app-server / hooks trust、codex-review skill stdin entry、wrapper role の実起動は別の条件を満たす環境で確認する必要がある。実ユーザー auth を隔離 HOME に symlink して確認する案は auto-review が情報漏えいリスクを理由に拒否したため、試していない。従って実ユーザー認証下での app-server、codex-review、wrapper role は未検証のままである。
- F-538-31 の残る限界として、猶予後の `killpg(SIGKILL)` は、グループの全メンバーが消えて PGID が再利用される
  極小の窓を完全には閉じない。SIGKILL の直前に存在確認を別の呼び出しで行うことはやめたが、PGID 再利用自体は防げない。
- 環境の2段の制限はラッパー経由の起動に適用される。実際の Codex シェルに認証関連の変数が現れないことは
  TD の手順 7 で検証する。ラッパーを通さない起動の環境は本契約の制御対象に含めない。
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

## Codex に issue-start dispatch 経路が無いこと

Codex 側に issue-start hook は登録されていない（`.codex/hooks.json` は Bash の `agent-command-gate.sh` と
`adr-notify.sh` だけ）。Codex の `issue-implementer`／`issue-fixer` agent も置かないため、Codex から
それらを dispatch する経路そのものが無い。`issue_start/managed-entrypoints-v2.json` の `binding_transports` は
`claude` だけを宣言し、Codex の binding transport は置かない。退役の経緯と旧 wrapper の保存先は
[`.ai/rationale/issue-pipeline.md`](../../.ai/rationale/issue-pipeline.md)「Issue #603: Codex main-context 資産の退役」を参照する。

gate の判定順と Claude transport の marker／isolation 契約は
[`docs/tools/issue-start-and-branch-source.md`](../tools/issue-start-and-branch-source.md) を正とする。
Claude 経路の契約は supervisor の退役でも PR-B でも変更していない。

## 維持する境界

- `codex-review`（別モデルファミリによる第二意見レビュー）と `.codex/mcp/claude_review/`。
- `.codex/hooks.json` の既存PreToolUse hook構成。command gateには#371の工程ロール制限を追加する。
- worktree 所有台帳（`issue_start/worktree_ledger.py`）と `durable_lock.py`。
- Claudeのfixer markerとworktree isolation。初回Issue-startはac-designerへ移し、implementerは
  phase bindingと承認済み上流成果物を必須にする（旧初回入口へは戻さない）。

## 旧資産の扱い

#603でCodex主文脈用の旧custom agentとissue-pipeline skillは退役済み。
工程profileの追加を理由にこれらを復活させない。

## 記録の所在

| 記録 | 置き場 |
|---|---|
| 退役した supervisor 方式の実行契約・設計判断 | `.ai/rationale/codex-supervisor-retirement-538.md` |
| 主文脈を Claude Code とする決定の経緯 | `audit/2026-09-21-pipeline-redesign/README.md` |
| 実起動 spike の経緯・PR-B の設計確定事項 | Issue #538 本文・コメント |
| 実起動検証の設計 | `tests/designs/TD-codex-worktree-exec-538-001.md` |
| Issue #452 のテスト設計・テスト結果 | `archive/issue-452-codex-supervisor/` |
| Issue #452 のテストログ | `tests/logs/TD-issue-start-452-*` |


## read-only工程のprimary → linked準備

`issue_start.readonly_workspace` はtrusted主文脈専用の実行入口である。
主文脈はruntimeを選択し、既存の登録済み・信頼済みlinked作業面を指定する。
linked作業面を新設する必要があれば主文脈の既存worktree準備契約で先に準備し、
この入口自身にはworktree作成、branch採用、trust設定、profile pin更新をさせない。

```text
python3 -m issue_start.readonly_workspace --source /repo/primary --approval-file tmp/review-approval.json --role pr-reviewer -C /repo/linked --binding-file tmp/review-binding.json --prompt-file tmp/review-prompt.md --output-file tmp/review-result.md --model MODEL --reasoning-effort high
```

入口はread-only 4ロールだけを受け付け、native readonly dispatchのavailabilityと入力承認を
sourceで検査する。同じgit-common-dir、同じHEAD、両面のtracked cleanを要求する。
両面の未追跡集合も検査する。Git ignore設定は通常sourceやTCを許可する根拠にしない。
binding/approval/promptと初期入力・相談参照のtmpファイルを同じ相対pathへ転送する。
tmp外の参照は転送せずcommit bytes一致を検査し、symlink・escape・既存tmp入力との不一致を拒否する。
転送先で承認を再検証し、executorをlinked cwdから呼ぶのでD5のcwd/-C一致は変更しない。
D1/profile origin/main pin、project trust、nesting guard、read-only profileとロール別hookも全て適用する。
read-onlyロールのcommand gateにはこのprepare入口、任意cd、台帳操作、commit/pushを追加しない。
本番manifestのavailableは必須入力検査の免除ではない。未merge profile拒否は継続し、
fixtureでの到達をlive成功と呼ばない。

snapshot後の正規TD/TC/ADR/実装はtrusted callerが承認した正確なpathとsha256を
`binding.expected.source_changes` に保持する。過去review receiptのartifact digest/contextは凍結保持し、
source差分はtrusted binding検証で1回だけ照合する。nativeはbinding↔approval↔全receiptの
snapshot一致を要求するため、receipt側で後段source差分を再承認しない。
後段の実装差分を過去reviewが確認済みと見せず、進行承認とartifactレビューを別に検査する。
値nullはHEADで削除済みのpathだけを表す。全pathのHEAD bytesと作業面bytesを照合し、
承認外source変更は拒否する。同一Issueのcanonical envelopeもcommit済みであることを要求する。
これは承認済み差分の受け渡しであり、新しい承認権限や自動承認は作らない。

未追跡通常source・追加TCはnative/Codexの全工程とread-only準備の両作業面で拒否する。
`git ls-files --others -z` を使い、gitignoreやclone固有excludeは承認根拠にしない。
tmpの従来のデータ拡張子に加え、exact pathのlockだけを許可する：
`.ai/feedback/.writer.lock`、`.claude/scheduled_tasks.lock`、`tmp/_worktree/ledger.json.lock`、
`tmp/_karte/.writer.lock`、`issue_start/adr/.write.lock`、`issue_start/adr/.file-issue.lock`。
通常ファイルかつ非symlinkが必要で、ワイルドカード・ディレクトリ単位の例外を追加しない。

孤児 `__pycache__/*.pyc` は対応sourceが作業面・HEAD・indexに存在しない場合だけ例外とする。
sourceのあるcacheは従来どおり現在のHEAD bytesと標準compiler出力のcode bytesまで照合する。
stale cacheと別runtime cacheは拒否し、trusted callerが
`python3 -m codex_worktree_exec.cache_prune --apply` で明示回復する（既定dry-run）。
対象はGit未追跡の `__pycache__/*.pyc` 通常ファイルだけで検査自体はread-only。
cache pruneは削除をせず、Git indexの排他ロックを取得して再度未追跡状態を検査し、ファイル実体の同一性を確認したうえで作業面外へatomic renameする。置換や親ディレクトリの切替えを検出した場合は原本を戻すか保全先を示して停止する。元ファイルはunlinkしない。
旧形式の `.pyo` は非対応cacheとして拒否し、trusted caller が `untracked_recovery --apply` で原本を退避する。
`cache_prune --apply` は `.pyo` を削除しないため、その回復案を提示しない。

違反は最初の1件で打ち切らず、分類別件数・代表path・回復方法を集約報告する。
coverage出力はcoverage-html手順により作業面外に隔離する。通常比較は同じcommitのisolated detached worktreeを使用し、環境変数なしの全unittestを実行する。coverage側だけbytecodeを抑止し、両実行の失敗test ID集合・終了コードを照合する。両方が0でない限りHTML生成とdone判定を拒否する。
生成物はgitignoreを許可根拠にせず拒否する。trusted callerは
`python3 -m codex_worktree_exec.untracked_recovery` でdry-run確認し、
`python3 -m codex_worktree_exec.untracked_recovery --apply` の単一の処置で
作業面外の `review-system-quarantine-*` に元のパス構造で保全できる。
対象は旧runtime/stale/unsupported cache、.coverage/htmlcov、.serena、
未承認tmp（`tmp/_adr-notify/*.root`、`tmp/pr-diffs/*.diff`、
`tmp/_feedback/*.toml`、任意拡張子のtmp残骸等）。
通常source・追加TC・symlinkは対象にせず拒否維持。下書きも無断で削除せず原本保全し、
復元が必要なら保全先を確認して戻す。Git indexの排他ロック中に未追跡状態・種類・対象inode/mtimeを再検証し、同一FS上のatomic renameで保全できない場合は停止し、
外部の別FSへ無言コピー・削除しない。移動先はcheckout外の限定アクセス権の一時領域にする。
通常sourceとTCは引き続き拒否。profile pin（D1）・D5・project trust・read-only profile・
既存source_changesの承認条件を変えない。

native著作工程の進行承認JSONは、既存のrecipient/run/Issue/target/snapshot/context/reviewsに加え
`dispatch_target = {repository, branch_name, expected_oid}` を必須にする（JSON object）。
これは過去review receiptを書き換える情報ではなく、trusted主文脈が今回起動する取得対象の承認である。
phase承認とnative markerのIssue/repository/branch/OIDを相互照合し、検査cwdのoriginとHEADが同じrepository/OIDで
あることを起動前に要求する。初回1aでは承認branchは新規作成予定名、expected_oidはbase_oidであり、
base_refとsnapshotも実HEADへ一致させる。後続著作では検査作業面をdetachedに限り、承認branch上と別名branch上は拒否する。検査作業面がdetachedでも、
primary checkoutを含む他のworktreeが承認branchを掴んでいれば拒否し、worktree一覧を取れないときも拒否する。承認branchを掴むworktreeを拒否するのは、
そのworktreeが承認branchを掴んだままだと次作者のadopt-branch stage 4が必ず拒否し、起票済みの失敗作者entryが
最新ownerとして残って同branchで継続できなくなるためである。
detachedではbranch名を作業面から確かめられないため、その照合は台帳の最新owner、`git ls-remote` のremote exact OID照合、
adopt-branch stage 2のremote exact OID照合へ委ねる。作業面の準備手順はClaude issue-pipeline wrapperを正とする。
過去snapshot OIDと後続HEADは異なり得るため、既存のancestor検査・canonical artifact・正確なsource_changesによって
承認snapshotから現在の検査面までを検証する。Codexも同じartifact検証を使い、D5のcwd/-C一致を維持する。
native read-only工程の既存phase承認形式は維持し、既存PRの再レビューはその専用契約を使う。
dispatchはrepo全体checkの参照/木/DAG/AC・TD/TC/Red証拠検査と索引内参照実体のcommit一致を要求し、
入力artifactのID/pathが検査集合にない場合も拒否する。

## 2aから2bへのwork unit束縛

trusted callerは2a著作者、2a独立pr-reviewer、2b実装者とPR reviewerに単一の `expected.work_unit` を渡し、各phase承認JSONにも同じ `work_unit` を明示する。CP入力ではIDが `work_units` に一つだけ存在することを検査する。TestDesignの非空 `work_unit` はhandoff期待値と完全一致し、`input_refs` は承認CPのID一つ、`input_digest` はそのcommit済みCP bytesのSHA-256とする。VDはCPを介して参照する。

2a独立review receiptには既存のartifact/path/digest/context等に加え `work_unit` を必須とし、TestDesign・今回のphase承認へ一致させる。1a/1b等のreceiptにはこの欄を加えない。2bの既存CP bindingには `expected.test_design={artifact, artifact_digest}` の短い消費参照だけを追加する。Codex単独入力とnative入力は同じ `work_unit_binding` でCP/TDのbytes・単位・run/Issue/target/snapshotを照合し、nativeは消費参照と2a receiptのartifact/digestも完全一致させる。別の承認台帳は作らず、owner承認や独立レビューをこの参照から生成しない。同run/target内の別unit、unit欠落、CP外unit、別TDのレビューは拒否する。

本節は検査対象分類と回復の現行実装説明である。既存の正式な2.0承認形式・profile pin・D5・project trust・read-only profileは変更しない。
