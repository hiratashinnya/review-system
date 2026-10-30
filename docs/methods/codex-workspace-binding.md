# Codex 実行経路の現行契約（`codex_worktree_exec`）

Issue #452 の Codex repo supervisor 方式は Issue #538 の PR-A で退役した。退役した実行契約・設計判断・却下案は
[`.ai/rationale/codex-supervisor-retirement-538.md`](../../.ai/rationale/codex-supervisor-retirement-538.md) へ移設した。
本書は Issue #538 の PR-B で導入し、#371で工程ロールへ拡張した実行経路の現在の契約を記す。

## 結論

- **Codex は主文脈にしない。** 主文脈は Claude Code であり、Codex はサブ実行者として使う
  （オーナー決定・2026-09-22・Issue #538）。
- **Claude の工程ロールと `issue-fixer` は、自分の linked worktree で元ロールの権限を維持してCodexを起動できる。**
  経路は `python3 -m codex_worktree_exec`（`codex exec -C <worktree>` の薄いラッパー）だけである（D12）。
- **Codex は commit・push・PR 作成をしない。** network は無効で、`.git` へは書けない。commit・push・PR 作成は
  呼び出し側の Claude ロールが既存の `agent-command-gate` の下で行う。
- 権限境界は版管理した permission profile（`.codex/config.toml`）、両PFの既存command hook、
  Claude側gateの起動形検査、ラッパーの起動前検査で担う。#371は既存hookへ工程ロールを追加する。
- **Codex の `spawn_agent` で `issue-implementer`／`issue-fixer` を起動する経路は無い。**
  issue-start gate が常時 `ISSUE_START_TRANSPORT_UNAVAILABLE` で拒否する（後述）。

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
  -c shell_environment_policy.inherit="core" \
  -c model_reasoning_effort="<effort>" --output-last-message <最終応答> -
```

依頼文は、固定の前置き（委譲しない・commit/push しない・範囲外を変更しない・最後に要約を返す）に本文を
続けて stdin で渡す。sandbox や承認を迂回する flag は渡さない。ラッパーはモデルと推論予算の既定値を持たない（D10）。

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
config の最初の有効設定はトップレベルの `default_permissions = ":workspace"` とする。profile 選択を省略した
起動と `--sandbox read-only` 起動でも config を読み込めるようにするためで、ラッパーのロール別選択は
`-c default_permissions="<role>"` で上書きする。

- 著作/fixerは `extends = ":workspace"`（`-C` の worktreeへ書け、配下の `.codex/` と `.git/` は読取専用）。
- 調査・レビュー・adviserは `extends = ":read-only"` とし、編集権限を与えない。
- `[permissions.<role>.network]`：`enabled`・`allow_local_binding`・`dangerously_allow_all_unix_sockets`・
  `dangerously_allow_non_loopback_proxy` をすべて `false`。
- `[permissions.<role>.filesystem]`：`~/.codex/auth.json`・`~/.config/gh`・`~/.claude/.credentials.json`・`~/.ssh` を `deny`。

profile の構文は、パスを絶対パスか `~/` 始まりで書く。`unittest` の `tests/unit/test_codex_worktree_exec_assets.py` が、
先頭の既定設定とロール別profile・著作profileの同一性・network無効・認証情報パスのdeny を静的に検査する
（未指定・`--sandbox read-only` の実起動成功の代替ではない）。

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
| D4 | `--role` の値と呼び出し元 agent_type の一致を Claude 側 gate で検査する。ロールの allowlist は `GATED_ROLES` から `pr-reviewer` を除いて導出する（`codex_worktree_exec/roles.py` の `CODEX_EXEC_ROLES`。gate もここを読む）。gate の基底集合には加えず、書込ロール専用集合へ加える。 | 書込ロールを増減するときは `GATED_ROLES` と `.codex/config.toml` の profile を同時に変える。導出をやめると gate とラッパーの許可集合が別々に保守され、基底集合への追加は `pr-reviewer` にも書込経路を与える。 |
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
- F-538-30：ラッパーを通さない起動（`codex exec` の直接起動・`codex-review`・対話利用・agy の `codex_*`）には、
  `.codex/config.toml` の既定 `default_permissions = ":workspace"` が適用され、認証情報パスが読める（実測）。
  この状態は本 PR の前から存在し、本 PR が持ち込んだ退行ではない。ロール別の network 無効・認証情報 deny が
  適用されるのはラッパーが該当 profile を選択した起動である。既定は未指定起動の config 読込みを成立させるために
  必要であり、削除すると未指定起動と `--sandbox read-only` 起動が失敗する（実測⑨）。既定を認証情報 deny 付きの
  強化 profile にする対応は、2026-10-13 のオーナー判断で Issue #630 へ繰り延べた。D12 は「ラッパーが Codex に
  リポジトリを書かせる唯一の**許可された**経路」という規律であり、ラッパーを通さない起動を機械的に拒否するものではない。
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

## Codex `spawn_agent` の常時拒否

Codex の `spawn_agent` / `collaborationspawn_agent` で既知の `issue-implementer` / `issue-fixer` を
指定した dispatch は、issue-start gate が payload の詳細・cwd・ledger・GitHub API を読む前に
`ISSUE_START_TRANSPORT_UNAVAILABLE` で拒否する。malformed な payload でも理由は変わらない。
`issue_start/managed-entrypoints-v2.json` の `binding_transports` は `claude` だけを宣言し、
Codex の binding transport は置かない。

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

未追跡通常source・追加TCはnative/Codexの全工程入力検査とread-only準備の両作業面で拒否する。
未追跡の例外は `tmp/` 配下の通常ファイル（`.json` / `.md` / `.yaml` / `.yml` / `.txt` / `.log`）による
工程入力・prompt・handoff・結果、下記の生成元検証を通る `__pycache__/` の `.pyc`、
既存feedback writer lockと `tmp/_worktree/ledger.json.lock`、Gitが登録した別linked worktree自身だけである。
symlinkは例外にしない。
compiled cacheは現在HEADの通常 `.py` sourceと作業面bytesの一致を先に要求し、同sourceを
現在Pythonの標準compilerでcompileしたcode bytesとcache内容を読取比較する。cacheをdecode・実行しない。
現在runtimeのcache tagとoptimize 0/1/2だけを対象とし、code filenameはworktree内sourceの絶対path、
root相対path、`./` を付けたroot相対pathに限定する。文字列intern有無による標準marshal表現差だけを許す。
timestamp/checked-hash/unchecked-hashの標準headerを受けても、headerだけでsource由来とは見なさない。
通常Pythonの標準cache生成は許可するが、別source・未commit/変更済source・現在の期待code bytesと異なる旧cache・別runtime・
未対応compiler形式のcacheは拒否する。必要な場合はtrusted callerが現在の承認sourceから標準再生成してから起動する。
検査はread-onlyであり、cacheの自動削除・書換えやreadonly roleへの再生成権限追加はしない。
HEAD sourceの読取は1回の未追跡検査内でsource毎にまとめ、次の検査では再読する。永続cacheや新しい台帳は作らない。
この検査が保証するのはtrusted入口で開始した検査以後に渡す作業面の入力である。検査Python自身や
hookが起動前に読み込むcode/cacheの完全性は既存trusted入口の前提であり、後から遡って保証したとは扱わない。
binding・approval・raw Issue・promptも未commitなら `tmp/` に置く。`tmp/` 内の追加Python sourceも拒否する。
`source_changes` にpath/digestを追加しても未追跡通常sourceは許可せず、従来どおりHEAD bytesの一致を要求する。

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

本是正は同一PR内の2.0遷移の補完であり、共通guidanceに従い再bumpしない。新profileのlive未実測とD1/D5等の境界は既存契約どおりである。
