# agent-command-gate のコメントに記録された経緯と設計理由

フックの連続コメントから移設した原文。現行の判定はフックを正本とする。

## .claude/hooks/agent-command-gate.sh 元の 2 行目

```text
# PreToolUse(Bash) フックハンドラ（ホワイトリスト方式・Issue #227）。
#
# 役割:
#   "issue-implementer" / "issue-fixer" / "pr-reviewer" サブエージェント種別に対して、push と
#   レビュー操作の境界を機械的に強制する。merge はネイティブ deny と共有字句検査で全ロールから拒否する。
#     - issue-implementer: push・PR作成は可、merge は不可（実装→PR作成までで STOP）。
#     - issue-fixer:        push・PR作成は可、merge は不可（issue-implementer と同一境界）。
#                           初回実装ではなく**レビュー指摘を受けた是正ラウンド専用**の別ロールで、
#                           診断カルテ操作のため `python3 -m karte` だけが追加で許可される
#                           （カルテの書き手を1ロールに絞るための非対称・PYTHON_MODULES_BY_ROLE）。
#     - pr-reviewer:        PR review は可、push は不可。
#                           **ブランチ切替も不可**（Issue #502 観測2）: このロールは非 isolated で
#                           メインワークツリー上で動くため、`gh pr checkout` は呼び出し元の
#                           primary checkout を切り替えてしまい、戻し忘れると以後の
#                           `gitgate adopt-branch` が BRANCH_ADOPT_LOCAL_EXISTS で必ず失敗する。
#                           差分は `gh pr diff --no-compact` / `gh pr view` / `gitgate show-pr-diff|diff|log` で読める。
#   gh-create-issue は GATED_ROLES の push/merge/worktree 契約には参加せず、専用の狭い gh/git 読取 allowlist
#   と `gh issue create`／限定 Project item 操作だけを許可する（Issue #632）。dispatch target は cwd の
#   GitHub origin から fail-close で確定し、全 `gh --repo/-R`・REST endpoint・Project item の Issue repository を照合する。
#   origin 不明または不一致なら deny する。それ以外の agent_type
#  （main／general-purpose／各 *-author 等・agent_type 欠如を含む）はロール専用判定対象外＝許可
#   （下記 2026-07-11 のオーナー判断）。ただし全 agent_type 共通の危険コマンド（network/exec）は deny する。
#
# 設計転換の経緯（Issue #227・2026-07-13 オーナー判断）:
#   #189→#213→#215→#218→#222 と6ラウンド以上、「危険/安全パターンを個別に列挙して検知する」方式で
#   改修を重ねたが（ヒアドキュメント・here-string・xargs・パイプ・サブシェル・fd複製…）、レビューの
#   たびに未列挙の亜種でバイパスされ続けた（40件超）。約800行が producer/passthrough 追跡機構に
#   費やされ、over-deny 回帰まで発生した。オーナー判断で「列挙による検知」自体がいたちごっこの構造
#   要因と診断し、**「本当に必要なコマンドの形だけを許可し、それ以外は一律禁止」**へ転換した。
#   バイパスは全て `|` `$()` backtick `<<` `<<<` `&&` `(` `)` 等の記号を悪用するものであり、記号自体を
#   締め出すことで「未列挙の亜種」という問題設定そのものを構造的に消す。
#
# 判定（対象ロールのみ・3層すべてを通過したときだけ許可）:
#   層1: 危険記号の quote-aware スキャン（dangerous_shell_symbol）
#        - クォート外（unquoted）: `| & ; ( ) { } < > $ ` 改行` → deny（パイプ・サブシェル・
#          ブレース展開・コマンド置換・リダイレクト・ヒアドキュメント・チェイン・複数行を記号レベルで
#          締め出す）。ブレース `{ }` は bash のトークン後展開で層3 判定を回避するため含める（F1）。
#        - ダブルクォート内: `$` と backtick のみ deny（`"$(...)"`・`"`...`"`・`"$VAR"` が有効なため）。
#          `( ) | ; < >` はダブルクォート内では**リテラル**なので許可する——本リポジトリの慣習である
#          conventional-commit タイトル `gh pr create --title "fix(hooks): ..."` を over-deny しないため
#          （quote-aware にする必然性はここにある。Issue #227 プラン「重要な設計理由」）。
#        - シングルクォート内: すべてリテラル → 無視（シングルクォートからは脱出できない）。
#        - バックスラッシュのエスケープを正しく追う（`\'` を「クォート開始」と誤認するとクォート状態が
#          bash とずれ、`git \' ; git merge evil ; \'` 型の見逃しが生じるため必須）。
#   層2: 先頭語ホワイトリスト（head_command_violation）
#        strip_wrappers_or_env_reason（rtk/command/builtin/exec の純ラッパーのみ剥がす。先頭 env 代入・
#        `env` ラッパーは層3 前処理で deny）後の先頭語が
#        `git` / `gh` / `pyright` / `python`・`python3`（**`-m` ＋ unittest|coverage|dsv2|gitgate|asset_parity|maintainability_lint|
#        time_fixture_lint|feedback_ledger、加えてロール別追加分＝issue-fixer のみ karte の形のみ、
#        issue-implementer/issue-fixer のみ codex_worktree_exec を `--role <自ロール>` の形のみ**）で
#        なければ deny。bash/sh/eval/source/xargs/curl/cat/echo/sed/awk/cut/rev/tee… は列挙不要で全 deny
#        （ホワイトリストに無い＝禁止）。パス付き（`./git` 等）も完全一致しないため deny。
#        asset_parity/time_fixture_lint は read-only 監査コマンド（`check` サブコマンドのみ実装）で、
#        coverage/karte と同型でサブコマンドを `check` に絞る（Issue #385・#129 の抜け穴を拡大しない）。
#        feedback_ledger（Issue #522）は書込み verb を持つため、ロール別の read-only 集合
#        （check/status/index）だけを通す（FEEDBACK_LEDGER_SUBCOMMANDS_BY_ROLE）。
#        `pyright` は node バイナリの型検査ツールで python モジュールではないため先頭語として追加した
#        （Issue #510）。層3 でも書込系・対話系フラグだけを狙い撃ちで deny する（後述）。
#   層3: ロール別許可判定（role_command_violation・Issue #227 追加修正3で git ラッパー方式へ転換）
#        gated ロールは Git の限定的な読み取りに加え、gitgate verb と許可済み GitHub CLI 操作を使える。
#        - 先頭 env 代入（`NAME=value`）・`env` ラッパーは deny（`rtk`/`command`/`builtin`/`exec` の純
#          ラッパーのみ剥がして内側を再検査）。
#        - git: status/log/diff/show/rev-parse は読み取りとして許可し、それ以外は gitgate に限定する。
#          `--output` と外部 diff/textconv は拒否し、ユーザ制御の書込み・外部実行フラグを通さない。
#        - gitgate: `python3 -m gitgate <verb>` の verb をロール別集合（impl: status/add/commit/
#          push/branch-current/new-branch/fetch/diff/log／fixer: それ＋adopt-branch／
#          reviewer: diff/log）で allow/deny する（層2 で gitgate モジュールは許可済み・ここで
#          verb を追加チェック）。worktree 解放系 verb（worktree-release/collect-worktree/
#          worktree-forget）はどのロールにも付与しない＝allowlist 未登録の既定 deny。
#        - gh: `--repo`/`-R` の値スキップのみ先頭で許容・他の先頭 `-*` は deny。サブコマンド
#          （pr/issue は第2トークンも）がロール別集合（impl/fixer: pr create/list/view, issue view, api／reviewer:
#          pr list/view/diff/checks/comment/review, issue view, api。`pr checkout` は許可しない）に
#          無ければ deny。さらに
#          **per-subcommand フラグ許可リスト**で未知フラグ・`--web`/`--editor` 等の外部起動フラグを deny する。
#        - pyright: gh と同型の**フラグ許可リスト方式**（PYRIGHT_FLAG_ALLOWLIST）で絞る
#          （Issue #510→F-510-03）。診断用の安全なフラグ（`--outputjson`/`--stats`/`--verbose`/
#          `--pythonversion`/`--pythonplatform` 等）と位置引数（型検査対象ファイル）だけを許可し、
#          それ以外は一律 deny する。元実装は「書込系 `--createstub`・対話系 `-w`/`--watch` だけを
#          個別に拒否する」denylist だったが、`--pythonpath`/`--venvpath`/`-v`/`--project`/`-p`/
#          `--typeshedpath` のような**インタプリタ起動・設定ファイル読込を伴うフラグ**が
#          素通りしていた（F-510-03・gh の denylist 放棄＝Issue #227 と同じ理由で allowlist へ転換）。
#        これで再レビュー Critical（`git push --receive-pack=…`・`git log/diff --output=…`）や別名サブ
#        コマンド・config/alias/env 注入による push/merge 迂回（`git send-pack`/`git subtree push`/
#        `git pull`/`git -c alias.x=push`/`gh api …/merge`/`gh alias set` 等）を列挙不要で fail-close 遮断する。
#
# 全 agent_type 共通の危険コマンド deny 層（Issue #224 フォローアップ・案B・2026-07-19）:
#   settings.json の permissions.deny（`Bash(curl *)` 等）は Claude Code 側の静的プレフィックスマッチで
#   あり、`FOO=x curl`（env代入プレフィックス）・`/usr/bin/curl`（絶対パス）・`true; curl`（compound
#   command）で機械的にすり抜けることが実証された（Issue #224）。中間ワイルドカード `Bash(*curl*)` は
#   `echo "curl"` のような無害な文字列まで over-match するため不採用。
#   上記の対象ロール専用の3層判定とは別に、**agent_type を問わず**（main context 自身・
#   issue-implementer・issue-fixer・pr-reviewer・各 *-author 等すべて）command 文字列を SEGMENT_SPLIT_RE
#   （`;`/`&&`/`||`/`|`/`(`/`)`/改行/`$(`/backtick）で素朴に（quote-aware ではなく）セグメント分割し、
#   各セグメントを shell_words でトークン化し、**セグメント内の全独立トークン**の os.path.basename を
#   判定する（PR #237 critical 修正・オーナー承認済み「独立トークン一致」。旧「先頭語のみ」判定は
#   `timeout 5 curl x`・`nice curl x`・`xargs curl x`・`echo x & curl y`・`{ curl z; }`・`sudo curl x`
#   のように危険コマンドを非先頭トークンに置くだけで記号ゼロですり抜けた＝#227 が脱却した denylist
#   いたちごっこの再来だった）。
#     - NETWORK_COMMANDS（curl/wget/nc/ncat/netcat/socat/telnet/ftp/tftp/ssh/scp/sftp/rsync）が
#       **いずれかの独立トークン**として現れれば deny（`timeout curl`・`sudo curl` 等の wrapper 経由も捕捉）。
#     - インタプリタの任意実行フォーム（同一セグメント内に `bash`/`sh`/`zsh`/`dash` トークン + `-c`
#       トークン、`python`/`python3` + `-c`、`perl`/`ruby`/`node` + `-e`、または `eval`/`source` トークン、
#       またはコマンド位置の `.`）も deny。**`python3 -m <module>` は `-c` トークンを持たないため allow を厳守**。
#     - トークン一致なので、クォートで1トークンになった文字列（`git commit -m "fix curl bug"`）や部分
#       文字列（`python3 test_curl.py`）は巻き込まない（over-match しない）。`.` はカレントディレクトリ
#       引数（`git add .`）への over-deny を避けるためコマンド位置のみ判定する。
#   SEGMENT_SPLIT_RE はダブルクォート/シングルクォートの内外を区別しない（quote-aware ではない）ため、
#   例えば `gh pr create --title "fix(hooks): ..."` の丸括弧でもセグメントは分割されるが、その結果
#   生じる断片はクォートが対応しなくなり shell_words でのトークン化に失敗し、単に読み飛ばされる
#   （**fail-open**＝over-match を避けるための意図的な設計。厳格な quote-aware 判定は対象ロール専用の
#   層1〜3が別途担う）。この deny 層は対象ロールにも前置適用されるが、層1（記号の一律 deny）が
#   既に更に厳格なため実質的な影響はない。
#
# 既知の限界（多層防御の一枚に過ぎない・Issue #129）:
#   - シェル文字列の静的検査であり sandbox ではない。agent_type の詐称・ハーネス外の実行経路は防げない。
#   - `python3 -m unittest|coverage` はリポジトリ内の Python コードを実行する＝テストファイル経由で
#     任意コードを走らせられる（テスト実行を許可する以上、原理的に閉じられない）。
#   - Gated roles deny Git writes and unlisted GitHub CLI commands; the shared hook checks merge operations for all roles.
#     `gitgate` and the allowed test runners execute repository Python code, so test files can still run arbitrary code.
#   pr-reviewer.md / issue-implementer.md / issue-fixer.md 側のプロンプトレベルの絶対規範と併用する前提。
#
# 入力: PreToolUse フックの stdin JSON（agent_type/subagent_type と tool_input.command を想定）。
#   command が読めない場合は検査不能として deny する。
#
#   2026-07-11 是正の経緯：Issue #129 対応で「agent_type 欠如時は危険コマンドを fail-closed で deny」
#   を追加したところ、main context 自身（agent_type を持たない）の git push まで塞ぐ回帰が発生した。
#   オーナー判断：①main context 自身を識別するタグ付けはハーネス側の機能が必要でこのフックだけでは
#   実現不可、②push/merge を専用エージェント以外全面禁止する案は main context の直接 push まで
#   止めるコストが大きく不採用。よって「対象外ロールは常に許可」という元の設計に確定して戻す
#   （fail-closed 化による agent_type 詐称防御は失うが、二者択一の上でのオーナー明示判断）。
#   Issue #227 でもこの fail-open 設計は**変更しない**（対象は GATED_ROLES のみ）。
# デバッグ: AGENT_COMMAND_GATE_DEBUG_PAYLOAD=/path/to/log を設定すると、受信 payload の redacted JSON と
#   判定を追記する（オプトイン・機微値はキー名ベースで伏せる）。
# トレース（Issue #192・常時有効）: 呼ばれるたびに時刻・agent_type・tool_name・判定(allow/deny)のみを
#   既定で ~/.claude/agent-command-gate-trace.log に1行追記する（command 本文・生 payload は含まない）。
#   パスは AGENT_COMMAND_GATE_TRACE_LOG で上書き、空文字で無効化できる。詳細は .codex/hooks/README.md 参照
#   （Codex 版と同じ設計。Claude 版の README には現状フック一覧の記載がないため参照先を明記）。
#
# 標準ライブラリのみで JSON をパースする（jq 非依存・CLAUDE.md の "python3 標準ライブラリのみ" 方針に合わせる）。
# 実装注意: `python3 - <<EOF ... EOF` は heredoc がそのまま python の stdin になり、外側で
# パイプされた本来の stdin（フック入力 JSON）が読めなくなる。よって stdin を一旦ファイルに
# 落としてから python にファイル引数として渡す。
```

## .claude/hooks/agent-command-gate.sh 元の 165 行目

```text
# GATED_ROLES の正本は issue_start/gated_roles.py（F-510-08・2ファイル重複定義の解消）。
# フックの呼び出し元 cwd は自由に変わるため、シェル側でフック配置位置から得たプロジェクトルートを使う。
# import 失敗時は下の `sys.excepthook`
# （`deny_on_internal_error`）がまだ設定されていないため Python の既定挙動で非0終了するが、
# 外側の bash ラッパー（本ファイル末尾）が「stdout 空 かつ rc 非0」を内部エラーとして検知し
# 一般化した deny メッセージを返す＝fail-close は維持される。
```

## .claude/hooks/agent-command-gate.sh 元の 185 行目

```text
# Issue #303: context-mode の実行系 MCP ツール（`ctx_execute` / `ctx_execute_file` /
# `ctx_batch_execute`）。これらは任意のコードをサブプロセスで実行でき、実測でホストの
# リポジトリ直下に書き込める（"sandboxed subprocess" はコンテキストのサンドボックスであって
# FS のサンドボックスではない）。settings.json の matcher は完全一致文字列で登録するが、
# サーバ名部分が変わってもマッチが外れて素通りしないよう、ここでも suffix で同定し直す。
```

## .claude/hooks/agent-command-gate.sh 元の 192 行目

```text
# `ctx_execute` / `ctx_execute_file` の language 許可リスト。shell 以外は
# `<interpreter> -c <code>` と意味論的に同値であり、universal 層（SCRIPT_EVAL_INTERPRETERS）と
# settings.json permissions.deny が**全 agent_type に対して既に禁止している**形。
# 非 shell 言語のコードは静的検査で安全に扱えない（言語ごとに複数のサブプロセス起動 API があり、
# 文字列結合・eval・動的 import でトークン一致は自明に回避できる＝Issue #227 が構造的に放棄した
# denylist いたちごっこの再来）ため、ここでは言語そのものを allowlist で絞る。
```

## .claude/hooks/agent-command-gate.sh 元の 200 行目

```text
# 層3（Issue #227 追加修正3・オーナー確定 2026-07-13）: git ラッパー方式＋gh フラグ許可リスト。
# gated ロールは限定された Git 読み取りを直接実行できる。Git の書込み・その他の操作は固定テンプレートの
# `python3 -m gitgate <verb>` に限定し、verb はロール別集合で判定する。
# gh は per-subcommand の**フラグ許可リスト**で絞り、未知フラグ・`--web`/`--editor` 等の外部起動フラグを
# deny する。config/alias/global-option/env 代入は git/gh とも従来どおり一律 deny。
# これで再レビュー Critical（`git push --receive-pack=…` の外部プログラム実行・`git log/diff --output=…`
# の任意ファイル書込）や別名サブコマンド経由の push/merge 迂回（`git send-pack`/`git subtree push`/
# `git pull`/`git -c alias.x=push`/`gh api …/merge`/`gh alias set`）を、静的なフラグ列挙に頼らず
# 構造的に遮断する（サブコマンド以降の引数を自由にしない）。
#
# Role permissions stay in the tables checked by `missing_role_tables`.
# Worktree release verbs remain limited to the main context and `SubagentStop` hook.
```

## .claude/hooks/agent-command-gate.sh 元の 239 行目

```text
# gh の per-subcommand フラグ許可リスト（Issue #227 追加修正3）。各 (sub, subsub) に value フラグ
# （値を取る＝次トークンまたは `=`/連結を値として消費）と bool フラグ（値なし）の許可集合を定める。
# ここに無い `-*` フラグは deny する。`--web`（ブラウザ起動）・`--editor`（エディタ起動）等の
# exec/外部起動フラグはどの集合にも入れない。`--repo`/`-R`（値）は全 subcommand 共通で許容する
# （GH_COMMON_VALUE_FLAGS）。監査根拠は gh 2.45.0 の `gh <cmd> --help`（各フラグの short/long とセマンティクス）。
```

## .claude/hooks/agent-command-gate.sh 元の 281 行目

```text
# 層1（Issue #227）: クォート外で禁止する記号。パイプ `|`・バックグラウンド/fd複製 `&`・チェイン `;`・
# サブシェル `( )`・ブレース展開 `{ }`・リダイレクト/ヒアドキュメント/here-string `< >`・
# コマンド置換 `$` backtick・改行（複数行＝複数コマンド）。これらを記号レベルで締め出すことで、
# #189〜#222 の40件超のバイパス（すべてこれらの記号を悪用する）を個別列挙なしに一括で塞ぐ。
# ブレース `{ }` は bash がトークン化後に展開するため（`git m{e..e}rge`→`git merge`・
# `git {merge,status}`→2語）、shlex ベースの層3 判定と bash 実行が乖離してバイパスになる（Issue #227
# レビュー F1）。`( ) | $` 等と同じくクォート外で一律 deny することで構造的に塞ぐ。
```

## .claude/hooks/agent-command-gate.sh 元の 294 行目

```text
# 層2（Issue #227）: 先頭語ホワイトリスト。ここに無い先頭語は一律 deny（列挙不要）。
# `pyright`（Issue #510）: node バイナリの型検査ツール。gated ロールが自分の受入基準
# （reportOptionalMemberAccess 等）を自分で検証できるようにするための追加。書込系・対話系
# フラグは層3 の pyright_violation() で個別に拒否する（下記）。
```

## .claude/hooks/agent-command-gate.sh 元の 300 行目

```text
# python は「モジュール実行（-m）で、かつ以下のモジュール」に限る（オーナー確定）。
# `python3 -c ...`・素の `python3 script.py`・その他のモジュールは deny。
# 第2次修正（オーナー確定 2026-07-15）: pytest は任意 path/conftest/plugin を実行する構造で絞れないため
# 除外（この repo は unittest 方針・CLAUDE.md）。coverage は run を禁止し report/html/xml/json のみ許可
# （`coverage run <なんでも>` は任意 Python 実行経路のため）。「-c 禁止したのに coverage run 素通し」の
# 不整合を消し、エージェントの混乱・ハルシネーションリスクを下げる（防御力は #129 限界のため不変）。
```

## .claude/hooks/agent-command-gate.sh 元の 311 行目

```text
# `asset_parity`/`time_fixture_lint`（Issue #385）: CI が回している read-only 監査コマンド
# （`python3 -m asset_parity check`・`python3 -m time_fixture_lint check`）。両ツールとも argparse
# ベースの固定 CLI でサブコマンドは `check` のみ実装し（`asset_parity/cli.py`・`time_fixture_lint/cli.py`）、
# 自分自身は4ツリー／tests 配下のいずれにも書き込まない（docstring で明記済み）。任意コード実行経路を
# 持たないため、`dsv2`/`gitgate` と同格の「コーパス/監査ツール」として基底集合に加える。
# **base集合に加える**のは coverage/karte のような「特定ロール限定」ではなく、issue-implementer/
# issue-fixer/pr-reviewer の3ロール全員が read-only 監査に使えるべきという Issue #385 の判断による。
# ロール別の**追加**モジュール（Issue #308）。基底集合 ALLOWED_PYTHON_MODULES に上乗せする形でのみ
# 使い、基底から差し引く用途には使わない（絞りたくなったら基底側を直す）。
#
# `karte` は issue-fixer（診断カルテの書き手）と pr-reviewer（自分の指摘の取り込み・Issue #375）
# にだけ足す。基底集合に入れて全 gated ロールへ配ると、書込経路が意図しないロールにまで生える。
# `karte` 自体は argparse の固定 CLI で任意コード実行経路を持たず、書き先も repo-root 配下の
# `tmp/_karte/` に fail-close で限定されている（`karte/paths.py`）。使える verb は下の
# KARTE_SUBCOMMANDS_BY_ROLE でロールごとに絞る。
```

### #696 側の移設元にあった旧説明

以下は #696 側の移設元の原文であり、Issue #375 による reviewer 本人の限定的な取り込み許可より前の説明である。現行のロール別許可はフックを正本とする。

```text
# `karte` を issue-fixer にだけ足すのは、カルテ（`tmp/_karte/issue-<N>.md`）の**書き手を
# issue-fixer に一本化する**という Issue #308 の設計をここでも機械的に担保するため。
# `python3 -m karte append` はカルテへの追記＝ループ状態の書き換えなので、基底集合に入れて
# 全 gated ロールへ配ると pr-reviewer（read-only・Write 非付与が fail-close の保証）にまで
# 書込経路が生えてしまう。`karte` 自体は argparse の固定 CLI で任意コード実行経路を持たず、
# 書き先も repo-root 配下の `tmp/_karte/` に fail-close で限定されている（`karte/paths.py`）ため、
# issue-fixer に限れば `dsv2` と同格の「コーパス操作ツール」として扱える。
```

## .claude/hooks/agent-command-gate.sh 元の 336 行目

```text
# `karte` は**状態を書き換える verb を持つ**ため、モジュール単位ではなく verb 単位で絞る
# （Issue #341 レビュー F-341-04）。`coverage` の `run` を禁じているのと同じ方式。
#
# **`ingest-review` を issue-fixer に許さない**のが要点：これは「レビューアの指摘を台帳へ取り込む」
# 手続きで、`status: resolved` を書ける。是正当事者がこれを実行できると、自作のレポートを `--from` で
# 食わせて未解消 finding を一括 resolved にし round を進められ、`append` の類似飽和拒否
# （#307 が入れたループ遮断）を迂回できてしまう＝「指摘した側」と「直す側」の分離が壊れる。
# `ingest-reviewer`（Issue #375）はレビューア本人の取り込みで、pr-reviewer だけに許す。申告以外の
# 台帳欄（disposition 系）は拒否・保持される。`ingest-review`・`activate`・`decide` はどのロールにも
# 許さない（主文脈専用）。この表は PYTHON_MODULES_BY_ROLE と同じく意図的に一部ロールだけを持つ。
```

## .claude/hooks/agent-command-gate.sh 元の 352 行目

```text
# asset_parity / time_fixture_lint（Issue #385）: 両ツールとも argparse 実装のサブコマンドは `check`
# のみ（`fix`/`apply`/その他の書込系サブコマンドは実装されていない）。coverage/karte と同型で verb 単位
# の allowlist を明示しておくことで、将来サブコマンドが増えても他が素通りしない構造にする
# （Issue #385 AC3・「サブコマンド制限の要否」への対応）。
```

## .claude/hooks/agent-command-gate.sh 元の 360 行目

```text
# `feedback_ledger`（Issue #522）: オーナー判断フィードバック台帳（`.ai/feedback/`）の
# **CLI 専用書込み**ツール。`karte` と同じく「状態を書き換える verb を持つ」ので、モジュール
# 単位ではなく **verb 単位・ロール別**に絞る（`GITGATE_VERBS_BY_ROLE` と同型の表なので、下の
# missing_role_tables 自己検査へ登録してある＝ロールの登録漏れが KeyError で素通しに化けない）。
#
# 3ロールとも **read-only の verb だけ**（`check`/`status`/`index`）を与える。要点は2つ。
#   * **是正当事者に `approve` を与えない**: 承認は週次棚卸しでのオーナー判断であり、
#     指摘を受けて直している当事者が自分の案を承認できると「指摘した側」と「直す側」の
#     分離が壊れる（`karte ingest-review` を issue-fixer に許さないのと同じ理由）。
#   * **書込み verb を誰にも与えない**: 台帳への記録・改訂案の起票・棚卸しの確定はいずれも
#     主文脈（非 gated）が行う。gated ロールが台帳を必要とするのは「今どうなっているかを
#     読む」ときだけなので、最小権限のまま read-only に留める。
```

## .claude/hooks/agent-command-gate.sh 元の 443 行目

```text
# 常時有効の最小トレース（Issue #192・.codex 版と同じ設計）：AGENT_COMMAND_GATE_DEBUG_PAYLOAD
# （オプトイン・フルペイロード・デフォルト無効）とは別に、"フックが実際に呼ばれたか" だけを常時
# 1行追記で残す。command 本文や生 payload は含めない（機微情報を持たない設計）。既定パスは
# AGENT_COMMAND_GATE_TRACE_LOG で上書きでき、空文字を設定すると無効化できる（テストや no-op 運用向け）。
```

## .claude/hooks/agent-command-gate.sh 元の 475 行目

```text
# Issue #340（#308 実装中に実踏）: このフックは末尾で必ず `exit 0` する。よって埋め込み Python が
# 未捕捉例外で落ちると **stdout が空のまま終わり、呼び出し側からは allow と区別が付かない**
# ＝内部エラーがそのまま権限ゲートの素通しに化ける。「検査できないものは deny する」という本フックの
# 他の判断（payload 破損・トークン化失敗・未知 MCP ツール）と揃えるため、未捕捉例外も deny に落とす。
# try/except ではなく excepthook で受けるのは、既存の判定ロジックを**再インデントせずに**全体を
# 覆えるため（数百行を囲うと diff が本質の変更を埋めてレビュー不能になる）。
# 注意: これは `GATED_ROLES` 外ロールの fail-open（2026-07-11 オーナー確定・ヘッダ参照）とは別物。
# あちらは「判定した上で許可する」設計判断、こちらは「判定しようとして落ちた」場合の話。
```

## .claude/hooks/agent-command-gate.sh 元の 497 行目

```text
# Issue #340: gated ロールは**ロール別 dict すべて**に登録されていなければならない。1つでも
# 欠けると該当ロールの判定が KeyError で落ちる（#308 で `GATED_ROLES` にだけ足して踏んだ）。
# 上の excepthook があれば deny に倒れるが、それは「壊れたまま止まる」であって正しい状態ではない
# ので、発生源で fail-close する。`PYTHON_MODULES_BY_ROLE` は**意図的に一部ロールだけ**を持つ
# 上乗せ表（既定は基底集合）なので、この全ロール必須の検査には含めない。
```

## .claude/hooks/agent-command-gate.sh 元の 942 行目

```text
# 層3(pyright・Issue #510→F-510-03): denylist ではなく **allowlist 方式**（gh の
# GH_FLAG_ALLOWLIST と同型）に統一する。旧実装は書込系フラグ（stub生成）と対話系フラグ
# （監視モード）だけを denylist で狙い撃ちしていたが、`--pythonpath`/`--venvpath`/`-v`/
# `--project`/`-p`/`--typeshedpath` のようなインタプリタ起動・設定ファイル読込を伴うフラグが
# 素通りしていた（F-510-03）。ここに無いフラグは一律 deny し、位置引数（型検査対象ファイル）は
# 自由（診断そのものを妨げない）。value フラグは値を取り（次トークンまたは `=`/連結）、
# bool フラグは値を取らない——gh_flag_violation と同じ消費規則。
```

## .claude/hooks/agent-command-gate.sh 元の 1731 行目

```text
    # 全 agent_type 共通の危険コマンド層（Issue #224 フォローアップ・案B）。対象ロール専用の層1〜3
    # より前に判定し、agent_type を問わず deny する（main context 自身・各 *-author 等の従来「常に許可」
    # だった穴を、settings.json permissions.deny では塞ぎ切れない env-prefix/abspath/compound 経路について
    # 補完する）。
```

## .claude/hooks/agent-command-gate.sh 元の 1755 行目

```text
    # agent_type が対象ロール以外（欠如を含む・main context 自身がこれに該当）はロール専用判定
    # （層1〜3）の対象外＝常に許可（ヘッダのオーナー判断・不変条件#1）。command 欠落でも許可する
    # （Codex 版と dispatch 順を統一・Issue #227 レビュー F3。対象ロールについては下で command 欠落→deny
    # を維持）。危険コマンドは上の全 agent_type 共通層で既に deny 済み。
```

## .claude/hooks/agent-command-gate.sh 元の 1778 行目

```text
# Issue #341 F-341-08: 埋め込み Python の `sys.excepthook`（#340）は**実行時例外しか捕まえられない**。
# 構文エラー（フック編集時にごく普通に起こる）ではモジュールがコンパイルされず excepthook が
# 設定される前に終わるし、`python3` 自体が無い・実行できない場合も同様で、どちらも
# 「stdout 空 ＋ 非0終了」になる。ここで受け止めないと従来どおり無条件 `exit 0` で
# **stdout 空＝allow** に落ち、#340 が塞いだはずの穴が同じ結果のまま残る。
#
# 判定は「stdout が空」だけに依らず **rc と併せて**見る：正常な allow も stdout は空なので、
# 「stdout 空 かつ rc 非0」のときだけ内部エラーとみなす（正常 allow を deny に化けさせない）。
```


## .codex/hooks/agent-command-gate.sh

### 元の 2 行目

```text
# Codex CLI PreToolUse フックハンドラ（.claude/hooks/agent-command-gate.sh の Codex 版・
# ホワイトリスト方式・Issue #227）。
#
# 役割:
#   "issue-implementer" / "issue-fixer" / "pr-reviewer" subagent（Codex custom subagent の role 名）に
#   対して、push とレビュー操作の境界を機械的に強制する。merge は両 PF の all-role hook 判定で拒否し、
#   native execpolicy は直接形の command prefix を対象にする。global options、wrapper、API、検査可能な
#   間接実行形は hook が判定する。
#     - issue-implementer: push・PR作成は可、merge は不可（実装→PR作成までで STOP）。
#     - issue-fixer:        push・PR作成は可、merge は不可（issue-implementer と同一境界）。
#                           初回実装ではなく**レビュー指摘を受けた是正ラウンド専用**の別ロールで、
#                           診断カルテ操作のため `python3 -m karte` だけが追加で許可される
#                           （カルテの書き手を1ロールに絞るための非対称・PYTHON_MODULES_BY_ROLE）。
#     - pr-reviewer:        PR review は可、push は不可。
#                           **ブランチ切替も不可**（Issue #502 観測2・両ツリー同時）: `gh pr checkout` は
#                           レビューアが共有するワークツリーのブランチを切り替え、戻し忘れると以後の
#                           `gitgate adopt-branch` が BRANCH_ADOPT_LOCAL_EXISTS で必ず失敗する。
#                           差分は `gh pr diff --no-compact` / `gh pr view` / `gitgate show-pr-diff|diff|log` で読める。
#   それ以外の agent_type（main／各 *-author 等・agent_type 欠如を含む）はこのゲートのロール専用
#   判定（層1〜3）の対象外＝ロール専用判定は適用しない。ただし全 agent_type 共通 deny 層
#   （merge コマンド、および Issue #224 フォローアップ・案B の network/exec 危険コマンド。後述）は
#   対象外ロールにも適用されるため、対象外ロールでも merge と network/exec は deny され、
#   それ以外は従来通り許可される。
#
# Codex CLI 対応の一次資料（codex-cli 0.142.5 / openai/codex main で確認）:
#   - 入力スキーマ codex-rs/hooks/schema/generated/pre-tool-use.command.input.schema.json:
#       agent_type（任意・subagent の role 名が入る）／tool_name（必須）／tool_input（必須・任意型）等。
#   - 出力スキーマ codex-rs/hooks/schema/generated/pre-tool-use.command.output.schema.json:
#       hookSpecificOutput.{hookEventName:"PreToolUse", permissionDecision:"deny", permissionDecisionReason}
#       で拒否する。permissionDecision:"deny" は非空の permissionDecisionReason を要求する
#       （codex-rs/hooks/src/engine/output_parser.rs）。この deny ワイヤ形式は Claude Code と同一。
#   - シェルコマンドの tool_name は "Bash"、tool_input.command は文字列
#       （codex-rs/core/src/tools/hook_names.rs の HookToolName::bash()、
#        codex-rs/core/src/hook_runtime.rs で tool_input.command を string として参照）。
#   - agent_type は spawn された subagent の role 名（= .codex/agents/*.toml の name）
#       （codex-rs/core/src/hook_runtime.rs subagent_hook_context / SubagentHookContext.agent_type）。
#   - 登録形式は .codex/hooks.json の "PreToolUse": [{ "matcher": "Bash", "hooks": [...] }]
#       （codex-rs/config/src/hook_config.rs の HookEventsToml.pre_tool_use / MatcherGroup）。
#     プロジェクトローカルフックは初回に `/hooks` で trust する必要がある（trusted_hash）。
#
# 設計転換の経緯（Issue #227・2026-07-13 オーナー判断・Claude 版と同一設計）:
#   #189→#213→#215→#218→#222 と6ラウンド以上、「危険/安全パターンを個別に列挙して検知する」方式で
#   改修を重ねたが（ヒアドキュメント・here-string・xargs・パイプ・サブシェル・fd複製…）、レビューの
#   たびに未列挙の亜種でバイパスされ続けた（40件超）。約800行が producer/passthrough 追跡機構に
#   費やされ、over-deny 回帰まで発生した。オーナー判断で「列挙による検知」自体がいたちごっこの構造
#   要因と診断し、**「本当に必要なコマンドの形だけを許可し、それ以外は一律禁止」**へ転換した。
#   バイパスは全て `|` `$()` backtick `<<` `<<<` `&&` `(` `)` 等の記号を悪用するものであり、記号自体を
#   締め出すことで「未列挙の亜種」という問題設定そのものを構造的に消す。
#
# 判定（対象ロール・シェル系ツールのみ・3層すべてを通過したときだけ許可）:
#   層1: 危険記号の quote-aware スキャン（dangerous_shell_symbol）
#        - クォート外（unquoted）: `| & ; ( ) { } < > $ ` 改行` → deny（パイプ・サブシェル・
#          ブレース展開・コマンド置換・リダイレクト・ヒアドキュメント・チェイン・複数行を記号レベルで
#          締め出す）。ブレース `{ }` は bash のトークン後展開で層3 判定を回避するため含める（F1）。
#        - ダブルクォート内: `$` と backtick のみ deny（`"$(...)"`・`"`...`"`・`"$VAR"` が有効なため）。
#          `( ) | ; < >` はダブルクォート内では**リテラル**なので許可する——conventional-commit タイトル
#          `gh pr create --title "fix(hooks): ..."` を over-deny しないため（Issue #227 の必須要件）。
#        - シングルクォート内: すべてリテラル → 無視（シングルクォートからは脱出できない）。
#        - バックスラッシュのエスケープを正しく追う（`\'` を「クォート開始」と誤認するとクォート状態が
#          bash とずれ、`git \' ; git merge evil ; \'` 型の見逃しが生じるため必須）。
#   層2: 先頭語ホワイトリスト（head_command_violation）
#        strip_wrappers_or_env_reason（rtk/command/builtin/exec の純ラッパーのみ剥がす。先頭 env 代入・
#        `env` ラッパーは層3 前処理で deny）後の先頭語が
#        `git` / `gh` / `pyright` / `python`・`python3`（**`-m` ＋ unittest|coverage|dsv2|gitgate|
#        asset_parity|time_fixture_lint|maintainability_lint、加えてロール別追加分＝issue-fixer のみ karte の形のみ**）で
#        なければ deny。bash/sh/eval/source/xargs/curl/cat/echo/sed/awk/cut/rev/tee… は列挙不要で全 deny。
#        **例外（pr-reviewer のみ・層2・層3 の対象外）**: pr-reviewer だけは保存差分の読取として
#        `rtk sed -n <start>,<end>p tmp/pr-diffs/pr-<番号>-<32桁hex>.diff` の単一形を許可する。層1 を
#        通過後、gate_reason が先頭語 `sed` を pr_diff_read_violation で別検査し、
#        head_command_violation（層2）・role_command_violation（層3）の前に抜けるため、層2 の先頭語
#        一覧にも層3 の allowlist にも載らない。記述の正本は .codex/agents/pr-reviewer.toml。
#        asset_parity/time_fixture_lint は read-only 監査コマンド（`check` サブコマンドのみ実装）で、
#        coverage/karte と同型でサブコマンドを `check` に絞る（Issue #385・#129 の抜け穴を拡大しない）。
#        `pyright`（Issue #510→F-510-06）: node バイナリの型検査ツール。gated ロールが自分の受入基準
#        （reportOptionalMemberAccess 等）を自分で検証できるようにする（Claude 版 F-510-03 と同一設計を
#        Codex 側にも導入）。
#   層3: ロール別許可判定（role_command_violation・Issue #227 追加修正3で git ラッパー方式へ転換）
#        gated ロールは Git の限定的な読み取りに加え、gitgate verb と許可済み GitHub CLI 操作を使える。
#        - 先頭 env 代入（`NAME=value`）・`env` ラッパーは deny（`rtk`/`command`/`builtin`/`exec` の純
#          ラッパーのみ剥がして内側を再検査）。
#        - git: status/log/diff/show/rev-parse は読み取りとして許可し、それ以外は gitgate に限定する。
#          `--output` と外部 diff/textconv は拒否し、ユーザ制御の書込み・外部実行フラグを通さない。
#        - gitgate: `python3 -m gitgate <verb>` の verb をロール別集合（impl: status/add/commit/
#          push/branch-current/new-branch/fetch/diff/log／fixer: それ＋adopt-branch／
#          reviewer: diff/log）で allow/deny する。worktree 解放系 verb（worktree-release/
#          collect-worktree/worktree-forget）はどのロールにも付与しない＝allowlist 未登録の既定 deny。
#        - gh: `--repo`/`-R` の値スキップのみ先頭で許容・他の先頭 `-*` は deny。サブコマンド
#          （pr/issue は第2トークンも）がロール別集合（impl/fixer: pr create/list/view, issue view, api／reviewer:
#          pr list/view/diff/checks/comment/review, issue view, api。`pr checkout` は許可しない）に
#          無ければ deny。さらに
#          **per-subcommand フラグ許可リスト**で未知フラグ・`--web`/`--editor` 等の外部起動フラグを deny する。
#        - pyright（Issue #510→F-510-06）: gh と同型の**フラグ許可リスト方式**（PYRIGHT_FLAG_ALLOWLIST）
#          で絞る。診断用の安全なフラグと位置引数（型検査対象ファイル）だけを許可し、書込系
#          `--createstub`・対話系 `-w`/`--watch`・インタプリタ起動/設定ファイル読込を伴う
#          `--pythonpath`/`--venvpath`/`-v`/`--project`/`-p`/`--typeshedpath` はいずれも allowlist に
#          無いため一括で deny する（Claude 版 F-510-03 と同一実装）。
#        これで再レビュー Critical（`git push --receive-pack=…`・`git log/diff --output=…`）や別名サブ
#        コマンド・config/alias/env 注入による push/merge 迂回（`git send-pack`/`git subtree push`/
#        `git pull`/`git -c alias.x=push`/`gh api …/merge`/`gh alias set` 等）を列挙不要で fail-close 遮断する。
#
# 全 agent_type 共通の危険コマンド deny 層（Issue #224 フォローアップ・案B・2026-07-19・Claude 版と同一設計）:
#   settings.json（Claude 側）の permissions.deny 相当の静的プレフィックスマッチは `FOO=x curl`（env代入
#   プレフィックス）・`/usr/bin/curl`（絶対パス）・`true; curl`（compound command）で機械的にすり抜ける
#   ことが実証された（Issue #224）。中間ワイルドカード `*curl*` は `echo "curl"` のような無害な文字列
#   まで over-match するため不採用。
#   上記の対象ロール専用の3層判定とは別に、**agent_type を問わず**（main context 自身・
#   issue-implementer・issue-fixer・pr-reviewer・各 *-author 等すべて）command 文字列を SEGMENT_SPLIT_RE
#   （`;`/`&&`/`||`/`|`/`(`/`)`/改行/`$(`/backtick）で素朴に（quote-aware ではなく）セグメント分割し、
#   各セグメントを shell_words でトークン化し、**セグメント内の全独立トークン**の os.path.basename を
#   判定する（PR #237 critical 修正・オーナー承認済み「独立トークン一致」。旧「先頭語のみ」判定は
#   `timeout 5 curl x`・`nice curl x`・`xargs curl x`・`echo x & curl y`・`{ curl z; }`・`sudo curl x`
#   のように危険コマンドを非先頭トークンに置くだけで記号ゼロですり抜けた＝#227 が脱却した denylist
#   いたちごっこの再来だった）。
#     - NETWORK_COMMANDS（curl/wget/nc/ncat/netcat/socat/telnet/ftp/tftp/ssh/scp/sftp/rsync）が
#       **いずれかの独立トークン**として現れれば deny（`timeout curl`・`sudo curl` 等の wrapper 経由も捕捉）。
#     - インタプリタの任意実行フォーム（同一セグメント内に `bash`/`sh`/`zsh`/`dash` トークン + `-c`
#       トークン、`python`/`python3` + `-c`、`perl`/`ruby`/`node` + `-e`、または `eval`/`source` トークン、
#       またはコマンド位置の `.`）も deny。**`python3 -m <module>` は `-c` トークンを持たないため allow を厳守**。
#     - トークン一致なので、クォートで1トークンになった文字列（`git commit -m "fix curl bug"`）や部分
#       文字列（`python3 test_curl.py`）は巻き込まない（over-match しない）。`.` はカレントディレクトリ
#       引数（`git add .`）への over-deny を避けるためコマンド位置のみ判定する。
#   SEGMENT_SPLIT_RE はダブルクォート/シングルクォートの内外を区別しない（quote-aware ではない）ため、
#   例えば `gh pr create --title "fix(hooks): ..."` の丸括弧でもセグメントは分割されるが、その結果
#   生じる断片はクォートが対応しなくなり shell_words でのトークン化に失敗し、単に読み飛ばされる
#   （**fail-open**＝over-match を避けるための意図的な設計。厳格な quote-aware 判定は対象ロール専用の
#   層1〜3が別途担う）。この deny 層は対象ロールにも前置適用されるが、層1（記号の一律 deny）が
#   既に更に厳格なため実質的な影響はない。
#
# 既知の限界（Issue #129 / #181・多層防御の一枚に過ぎない）:
#   - シェル文字列の静的検査であり sandbox ではない。agent_type の詐称・ハーネス外の実行経路は防げない。
#   - `python3 -m unittest|coverage` はリポジトリ内の Python コードを実行する＝テストファイル経由で
#     任意コードを走らせられる（テスト実行を許可する以上、原理的に閉じられない）。
#   - Gated roles deny Git writes and unlisted GitHub CLI commands; the shared hook checks merge operations for all roles.
#     `gitgate` and the allowed test runners execute repository Python code, so test files can still run arbitrary code.
#   - Codex 側特有: (a) フックは `/hooks` で trust されて初めて発火する、(b) requirements.toml/config.toml で
#     フックが無効化され得る、(c) agent_type に実際どの文字列が入るかは dogfooding で最終確認すべき
#     （AGENT_COMMAND_GATE_DEBUG_PAYLOAD で受信 payload を確認できる）。
#   pr-reviewer.toml / issue-implementer.toml / issue-fixer.toml 側のプロンプトレベルの規範と併用する前提。
#
# 入力: PreToolUse フックの stdin JSON（agent_type と tool_name と tool_input.command を想定）。
#   判定順は gate 末尾の決定ブロックと一致する。まず全 agent_type 共通の deny 層（merge コマンド・
#   network/exec コマンド）を、欠如を含む全ロールへ適用する。agent_type が GATED_ROLES
#   （issue-implementer / issue-fixer / pr-reviewer・正本 issue_start/gated_roles.py）に含まれない場合
#   （欠如を含む）は、上記の共通 deny に掛からない限り許可し、ロール専用判定（層1〜3）は適用しない。
#   tool_name がシェル系（Bash 等）でない場合も許可する（git/gh は Bash 経由のため）。
#   GATED_ROLES でコマンド文字列が読めない場合は検査不能として deny する（fail-closed）。
#
#   Claude 版と同じオーナー判断を踏襲：agent_type 欠如時（main context 自身）にロール専用判定（層1〜3）の
#   対象へ含め fail-closed で deny すると main context の直接 push まで塞ぐ回帰が出るため、「対象外ロールは
#   常に許可」とする（共通 deny 層に掛からないものに限る・agent_type 詐称防御は失うが、二者択一の上での
#   オーナー明示判断・Claude issue #129）。
#   Issue #227 でもこの fail-open 設計は**変更しない**（対象は GATED_ROLES のみ）。
# デバッグ: AGENT_COMMAND_GATE_DEBUG_PAYLOAD=/path/to/log を設定すると、受信 payload の redacted JSON と
#   判定を追記する（オプトイン・機微値はキー名ベースで伏せる）。
# トレース（Issue #192・常時有効）: 呼ばれるたびに時刻・agent_type・tool_name・判定(allow/deny)のみを
#   既定で ~/.codex/agent-command-gate-trace.log に1行追記する（command 本文・生 payload は含まない）。
#   パスは AGENT_COMMAND_GATE_TRACE_LOG で上書き、空文字で無効化できる。詳細は README.md 参照。
#
# 標準ライブラリのみで JSON をパースする（jq 非依存・AGENTS.md の "python3 標準ライブラリのみ" 方針に合わせる）。
# 実装注意: `python3 - <<EOF ... EOF` は heredoc がそのまま python の stdin になり、外側で
# パイプされた本来の stdin（フック入力 JSON）が読めなくなる。よって stdin を一旦ファイルに
# 落としてから python にファイル引数として渡す。
```

### 元の 200 行目

```text
# 層3（Issue #227 追加修正3・オーナー確定 2026-07-13）: git ラッパー方式＋gh フラグ許可リスト。
# gated ロールは限定された Git 読み取りを直接実行できる。Git の書込み・その他の操作は固定テンプレートの
# `python3 -m gitgate <verb>` に限定し、verb はロール別集合で判定する。
# gh は per-subcommand の**フラグ許可リスト**で絞り、未知フラグ・`--web`/`--editor` 等の外部起動フラグを
# deny する。config/alias/global-option/env 代入は git/gh とも従来どおり一律 deny。
# これで再レビュー Critical（`git push --receive-pack=…` の外部プログラム実行・`git log/diff --output=…`
# の任意ファイル書込）や別名サブコマンド経由の push/merge 迂回（`git send-pack`/`git subtree push`/
# `git pull`/`git -c alias.x=push`/`gh api …/merge`/`gh alias set`）を、静的なフラグ列挙に頼らず
# 構造的に遮断する（サブコマンド以降の引数を自由にしない）。
#
# Role permissions stay in the tables checked by `missing_role_tables`.
# Worktree release verbs are granted to no gated role. Roles outside GATED_ROLES (e.g. the main
# context) are not constrained by this role table. This repo registers no SubagentStop-equivalent hook for Codex.
```

### 元の 240 行目

```text
# gh の per-subcommand フラグ許可リスト（Issue #227 追加修正3）。各 (sub, subsub) に value フラグ
# （値を取る＝次トークンまたは `=`/連結を値として消費）と bool フラグ（値なし）の許可集合を定める。
# ここに無い `-*` フラグは deny する。`--web`（ブラウザ起動）・`--editor`（エディタ起動）等の
# exec/外部起動フラグはどの集合にも入れない。`--repo`/`-R`（値）は全 subcommand 共通で許容する
# （GH_COMMON_VALUE_FLAGS）。監査根拠は gh 2.45.0 の `gh <cmd> --help`（各フラグの short/long とセマンティクス）。
```

### 元の 281 行目

```text
# Codex がシェルコマンドの hook tool_name として使う canonical 名は "Bash"
# （codex-rs/core/src/tools/hook_names.rs HookToolName::bash()）。git/gh はこの Bash ツール経由で走る。
# 将来 canonical 名が変わっても取りこぼさないよう、代表的なシェル系エイリアスも許容集合に入れる。
# 空文字（tool_name 欠如）は検査不能側に倒して inspect する（fail-closed 寄り）。
```

### 元の 287 行目

```text
# 層1（Issue #227）: クォート外で禁止する記号。パイプ `|`・バックグラウンド/fd複製 `&`・チェイン `;`・
# サブシェル `( )`・ブレース展開 `{ }`・リダイレクト/ヒアドキュメント/here-string `< >`・
# コマンド置換 `$` backtick・改行（複数行＝複数コマンド）。これらを記号レベルで締め出すことで、
# #189〜#222 の40件超のバイパス（すべてこれらの記号を悪用する）を個別列挙なしに一括で塞ぐ。
# ブレース `{ }` は bash がトークン化後に展開するため（`git m{e..e}rge`→`git merge`・
# `git {merge,status}`→2語）、shlex ベースの層3 判定と bash 実行が乖離してバイパスになる（Issue #227
# レビュー F1）。`( ) | $` 等と同じくクォート外で一律 deny することで構造的に塞ぐ。
```

### 元の 305 行目

```text
# python は「モジュール実行（-m）で、かつ以下のモジュール」に限る（オーナー確定）。
# `python3 -c ...`・素の `python3 script.py`・その他のモジュールは deny。
# 第2次修正（オーナー確定 2026-07-15）: pytest は任意 path/conftest/plugin を実行する構造で絞れないため
# 除外（この repo は unittest 方針・AGENTS.md）。coverage は run を禁止し report/html/xml/json のみ許可
# （`coverage run <なんでも>` は任意 Python 実行経路のため）。「-c 禁止したのに coverage run 素通し」の
# 不整合を消し、エージェントの混乱・ハルシネーションリスクを下げる（防御力は #129 限界のため不変）。
```

### 元の 316 行目

```text
# `asset_parity`/`time_fixture_lint`（Issue #385）: CI が回している read-only 監査コマンド
# （`python3 -m asset_parity check`・`python3 -m time_fixture_lint check`）。両ツールとも argparse
# ベースの固定 CLI でサブコマンドは `check` のみ実装し（`asset_parity/cli.py`・`time_fixture_lint/cli.py`）、
# 自分自身は4ツリー／tests 配下のいずれにも書き込まない（docstring で明記済み）。任意コード実行経路を
# 持たないため、`dsv2`/`gitgate` と同格の「コーパス/監査ツール」として基底集合に加える。
# **base集合に加える**のは coverage/karte のような「特定ロール限定」ではなく、issue-implementer/
# issue-fixer/pr-reviewer の3ロール全員が read-only 監査に使えるべきという Issue #385 の判断による。
# ロール別の**追加**モジュール（Issue #308）。基底集合 ALLOWED_PYTHON_MODULES に上乗せする形でのみ
# 使い、基底から差し引く用途には使わない（絞りたくなったら基底側を直す）。
#
# `karte` を issue-fixer にだけ足すのは、カルテ（`tmp/_karte/issue-<N>.md`）の**書き手を
# issue-fixer に一本化する**という Issue #308 の設計をここでも機械的に担保するため。
# `python3 -m karte append` はカルテへの追記＝ループ状態の書き換えなので、基底集合に入れて
# 全 gated ロールへ配ると pr-reviewer（read-only・ファイル書込を持たないことが fail-close の
# 保証）にまで書込経路が生えてしまう。`karte` 自体は argparse の固定 CLI で任意コード実行経路を
# 持たず、書き先も repo-root 配下の `tmp/_karte/` に fail-close で限定されている
# （`karte/paths.py`）ため、issue-fixer に限れば `dsv2` と同格の「コーパス操作ツール」として扱える。
```

### 元の 336 行目

```text
# `karte` は**状態を書き換える verb を持つ**ため、モジュール単位ではなく verb 単位で絞る
# （Issue #341 レビュー F-341-04）。`coverage` の `run` を禁じているのと同じ方式。
#
# **`ingest-review` を issue-fixer に許さない**のが要点：これは「レビューアの指摘を台帳へ取り込む」
# 手続きで、`status: resolved` を書ける。是正当事者がこれを実行できると、自作のレポートを `--from` で
# 食わせて未解消 finding を一括 resolved にし round を進められ、`append` の類似飽和拒否
# （#307 が入れたループ遮断）を迂回できてしまう＝「指摘した側」と「直す側」の分離が壊れる。
# 取り込みは主文脈（gated ロールではない）が行う。Claude 側の pr-reviewer 専用 verb
# `ingest-reviewer`（Issue #375）はこちらでは誰にも許さない（Codex の pr-reviewer は Write を持たない）。
```

### 元の 350 行目

```text
# asset_parity / time_fixture_lint（Issue #385）: 両ツールとも argparse 実装のサブコマンドは `check`
# のみ（`fix`/`apply`/その他の書込系サブコマンドは実装されていない）。coverage/karte と同型で verb 単位
# の allowlist を明示しておくことで、将来サブコマンドが増えても他が素通りしない構造にする
# （Issue #385 AC3・「サブコマンド制限の要否」への対応）。
```

### 元の 423 行目

```text
# 常時有効の最小トレース（Issue #192）：AGENT_COMMAND_GATE_DEBUG_PAYLOAD（オプトイン・フルペイロード・
# デフォルト無効）とは別に、"フックが実際に呼ばれたか" だけを常時1行追記で残す。command 本文や生 payload
# は含めない（機微情報を持たない設計）。既定パスは AGENT_COMMAND_GATE_TRACE_LOG で上書きでき、空文字を
# 設定すると無効化できる（テストや no-op 運用向け）。既定でオンにしたのは、オプトイン方式だと
# "trust 付与後に本当に発火したか" を確認したいまさにその時に、事前に環境変数を仕込み忘れて再現できない
# という Issue #192 の根本課題を再発させるため（1行判断根拠）。
```

### 元の 457 行目

```text
# Issue #340（#308 実装中に実踏）: このフックは末尾で必ず `exit 0` する。よって埋め込み Python が
# 未捕捉例外で落ちると **stdout が空のまま終わり、呼び出し側からは allow と区別が付かない**
# ＝内部エラーがそのまま権限ゲートの素通しに化ける。「検査できないものは deny する」という本フックの
# 他の判断（payload 破損・トークン化失敗・未知 MCP ツール）と揃えるため、未捕捉例外も deny に落とす。
# try/except ではなく excepthook で受けるのは、既存の判定ロジックを**再インデントせずに**全体を
# 覆えるため（数百行を囲うと diff が本質の変更を埋めてレビュー不能になる）。
# 注意: これは `GATED_ROLES` 外ロールの fail-open（2026-07-11 オーナー確定・ヘッダ参照）とは別物。
# あちらは「判定した上で許可する」設計判断、こちらは「判定しようとして落ちた」場合の話。
```

### 元の 479 行目

```text
# Issue #340: gated ロールは**ロール別 dict すべて**に登録されていなければならない。1つでも
# 欠けると該当ロールの判定が KeyError で落ちる（#308 で `GATED_ROLES` にだけ足して踏んだ）。
# 上の excepthook があれば deny に倒れるが、それは「壊れたまま止まる」であって正しい状態ではない
# ので、発生源で fail-close する。`PYTHON_MODULES_BY_ROLE` は**意図的に一部ロールだけ**を持つ
# 上乗せ表（既定は基底集合）なので、この全ロール必須の検査には含めない。
```

### 元の 919 行目

```text
# 層3(pyright・Issue #510→F-510-06): allowlist 方式（gh の GH_FLAG_ALLOWLIST と同型・Claude 版
# F-510-03 と同一実装）。診断用の安全なフラグと位置引数（型検査対象ファイル）だけを許可し、
# それ以外（書込系 `--createstub`・対話系 `-w`/`--watch`・インタプリタ起動/設定ファイル読込を
# 伴う `--pythonpath`/`--venvpath`/`-v`/`--project`/`-p`/`--typeshedpath` を含む）は一律 deny する。
```

### 元の 1249 行目

```text
# Issue #341 F-341-08: 埋め込み Python の `sys.excepthook`（#340）は**実行時例外しか捕まえられない**。
# 構文エラー（フック編集時にごく普通に起こる）ではモジュールがコンパイルされず excepthook が
# 設定される前に終わるし、`python3` 自体が無い・実行できない場合も同様で、どちらも
# 「stdout 空 ＋ 非0終了」になる。ここで受け止めないと従来どおり無条件 `exit 0` で
# **stdout 空＝allow** に落ち、#340 が塞いだはずの穴が同じ結果のまま残る。
#
# 判定は「stdout が空」だけに依らず **rc と併せて**見る：正常な allow も stdout は空なので、
# 「stdout 空 かつ rc 非0」のときだけ内部エラーとみなす（正常 allow を deny に化けさせない）。
```
