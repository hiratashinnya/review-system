#!/usr/bin/env bash
# PreToolUse(Bash) フックハンドラ（ホワイトリスト方式・Issue #227）。
#
# 役割:
#   "issue-implementer" / "issue-fixer" / "pr-reviewer" サブエージェント種別に対して、push と merge の
#   非対称な権限境界を機械的に強制する（プロンプト指示ではなくハーネス側で拒否する）。
#     - issue-implementer: push・PR作成は可、merge は不可（実装→PR作成までで STOP）。
#     - issue-fixer:        push・PR作成は可、merge は不可（issue-implementer と同一境界・Issue #308）。
#                           初回実装ではなく**レビュー指摘を受けた是正ラウンド専用**の別ロールで、
#                           診断カルテ操作のため `python3 -m karte` だけが追加で許可される
#                           （カルテの書き手を1ロールに絞るための非対称・PYTHON_MODULES_BY_ROLE）。
#     - pr-reviewer:        merge は可、push は不可（レビュー中に無レビューの変更を紛れ込ませられない）。
#   それ以外の agent_type（main／general-purpose／各 *-author 等・agent_type 欠如を含む）はこの
#   ゲートのロール専用判定（層1〜3）の対象外＝ロール専用判定は適用しない（下記 2026-07-11 の
#   オーナー判断）。ただし Issue #224 フォローアップ（案B・後述の「全 agent_type 共通の危険コマンド
#   deny 層」）を追加したため、対象外ロールも危険コマンド（network/exec）だけは deny され、それ以外は
#   従来通り許可される。
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
#        `git` / `gh` / `python`・`python3`（**`-m` ＋ unittest|coverage|dsv2|gitgate、加えて
#        ロール別追加分＝issue-fixer のみ karte の形のみ**）で
#        なければ deny。bash/sh/eval/source/xargs/curl/cat/echo/sed/awk/cut/rev/tee… は列挙不要で全 deny
#        （ホワイトリストに無い＝禁止）。パス付き（`./git` 等）も完全一致しないため deny。
#   層3: ロール別許可判定（role_command_violation・Issue #227 追加修正3で git ラッパー方式へ転換）
#        gated ロールに対し、生 git を一切禁止し gitgate ラッパー verb と gh サブコマンド/フラグだけを許可する。
#        - 先頭 env 代入（`NAME=value`）・`env` ラッパーは deny（`rtk`/`command`/`builtin`/`exec` の純
#          ラッパーのみ剥がして内側を再検査）。
#        - git: 生 `git …` は**全て deny**（raw_git_denied_reason）。git 操作は固定テンプレートの
#          `python3 -m gitgate <verb>` に誘導する（ユーザ制御フラグが git に届かない＝`--receive-pack`/
#          `--upload-pack`/`--output` 等の exec/write 面を構造的に閉じる）。
#        - gitgate: `python3 -m gitgate <verb>` の verb をロール別集合（impl/fixer: status/add/commit/
#          push/branch-current/new-branch/fetch/diff/log／reviewer: diff/log）で allow/deny する（層2 で
#          gitgate モジュールは許可済み・ここで verb を追加チェック）。
#        - gh: `--repo`/`-R` の値スキップのみ先頭で許容・他の先頭 `-*` は deny。サブコマンド
#          （pr/issue は第2トークンも）がロール別集合（impl/fixer: pr create / issue view／reviewer: pr
#          view/diff/checks/comment/review/merge/checkout・issue view）に無ければ deny。さらに
#          **per-subcommand フラグ許可リスト**で未知フラグ・`--web`/`--editor` 等の外部起動フラグを deny する。
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
#   - `git -c <key>=<value>`（alias!/core.pager 等）・`git push --receive-pack=…`・`gh api` 経由の merge・
#     別名サブコマンドでの push は Issue #227 追加修正3（生 git 全 deny＋gitgate ラッパー＋gh フラグ許可
#     リスト）で遮断済み。ただし gitgate は `python3 -m unittest|coverage` と同じく Python 実行を
#     許可する一枚に過ぎず、テストファイル経由の任意コード実行までは閉じられない（原理的限界）。
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
set -u

tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT
cat > "$tmpfile"

gate_out="$(mktemp)"
trap 'rm -f "$tmpfile" "$gate_out"' EXIT

set +e
python3 - "$tmpfile" > "$gate_out" <<'PYEOF'
import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone

SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|passwd|authorization|credential|key)", re.I)
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*", re.S)
WRAPPER_COMMANDS = {"rtk", "command", "builtin", "exec"}
GATED_ROLES = {"issue-implementer", "issue-fixer", "pr-reviewer"}

# Issue #303: context-mode の実行系 MCP ツール（`ctx_execute` / `ctx_execute_file` /
# `ctx_batch_execute`）。これらは任意のコードをサブプロセスで実行でき、実測でホストの
# リポジトリ直下に書き込める（"sandboxed subprocess" はコンテキストのサンドボックスであって
# FS のサンドボックスではない）。settings.json の matcher は完全一致文字列で登録するが、
# サーバ名部分が変わってもマッチが外れて素通りしないよう、ここでも suffix で同定し直す。
CTX_EXEC_TOOL_SUFFIXES = {"ctx_execute", "ctx_execute_file", "ctx_batch_execute"}

# `ctx_execute` / `ctx_execute_file` の language 許可リスト。shell 以外は
# `<interpreter> -c <code>` と意味論的に同値であり、universal 層（SCRIPT_EVAL_INTERPRETERS）と
# settings.json permissions.deny が**全 agent_type に対して既に禁止している**形。
# 非 shell 言語のコードは静的検査で安全に扱えない（言語ごとに複数のサブプロセス起動 API があり、
# 文字列結合・eval・動的 import でトークン一致は自明に回避できる＝Issue #227 が構造的に放棄した
# denylist いたちごっこの再来）ため、ここでは言語そのものを allowlist で絞る。
CTX_ALLOWED_LANGUAGES = {"shell"}

# 層3（Issue #227 追加修正3・オーナー確定 2026-07-13）: git ラッパー方式＋gh フラグ許可リスト。
# gated ロールからは**生 git を一切禁止**し、固定テンプレートで git を呼ぶ薄いラッパー
# `python3 -m gitgate <verb>` のみ許可する（ユーザ制御フラグが git に届かない＝exec/write 面を構造的に
# 閉じる）。verb はロール別集合で allow/deny する（gitgate 自体は全 verb を実装し、ロール制限はここが担う）。
# gh は per-subcommand の**フラグ許可リスト**で絞り、未知フラグ・`--web`/`--editor` 等の外部起動フラグを
# deny する。config/alias/global-option/env 代入は git/gh とも従来どおり一律 deny。
# これで再レビュー Critical（`git push --receive-pack=…` の外部プログラム実行・`git log/diff --output=…`
# の任意ファイル書込）や別名サブコマンド経由の push/merge 迂回（`git send-pack`/`git subtree push`/
# `git pull`/`git -c alias.x=push`/`gh api …/merge`/`gh alias set`）を、静的なフラグ列挙に頼らず
# 構造的に遮断する（サブコマンド以降の引数を自由にしない）。
GITGATE_VERBS_BY_ROLE = {
    # issue-implementer: 実装→push→PR まで。gitgate の全 verb を許可する。
    "issue-implementer": {
        "status", "add", "commit", "push", "branch-current",
        "new-branch", "fetch", "diff", "log",
    },
    # issue-fixer（Issue #308）: 是正ラウンド専用。権限は issue-implementer と**同一**
    # （push 可・merge 不可）。是正も「直して commit して push して PR を更新する」ので
    # 必要な git 操作は初回実装と変わらない。差は診断（カルテ）必須という契約の側にあり、
    # ここで verb 集合を絞っても是正の質は上がらず、ただ機能しなくなるだけ。
    "issue-fixer": {
        "status", "add", "commit", "push", "branch-current",
        "new-branch", "fetch", "diff", "log",
    },
    # pr-reviewer: レビューの読取専用のみ（diff/log）。
    "pr-reviewer": {"diff", "log"},
}
GH_SUBCOMMANDS_BY_ROLE = {
    # (subcommand, subsubcommand) の完全一致。pr/issue は第2 bare トークンまで見る。
    "issue-implementer": {("pr", "create"), ("issue", "view")},
    # issue-fixer は issue-implementer と同一集合（Issue #308）。`pr merge` は当然含めない
    # ＝merge は pr-reviewer の専権という非対称は是正ロールでも維持される。
    "issue-fixer": {("pr", "create"), ("issue", "view")},
    "pr-reviewer": {
        ("pr", "view"), ("pr", "diff"), ("pr", "checks"), ("pr", "comment"),
        ("pr", "review"), ("pr", "merge"), ("pr", "checkout"), ("issue", "view"),
    },
}
# gh の per-subcommand フラグ許可リスト（Issue #227 追加修正3）。各 (sub, subsub) に value フラグ
# （値を取る＝次トークンまたは `=`/連結を値として消費）と bool フラグ（値なし）の許可集合を定める。
# ここに無い `-*` フラグは deny する。`--web`（ブラウザ起動）・`--editor`（エディタ起動）等の
# exec/外部起動フラグはどの集合にも入れない。`--repo`/`-R`（値）は全 subcommand 共通で許容する
# （GH_COMMON_VALUE_FLAGS）。監査根拠は gh 2.45.0 の `gh <cmd> --help`（各フラグの short/long とセマンティクス）。
GH_COMMON_VALUE_FLAGS = {"--repo", "-R"}
GH_FLAG_ALLOWLIST = {
    ("pr", "create"): {
        "value": {"--title", "-t", "--body-file", "-F", "--base", "-B", "--head", "-H"},
        "bool": {"--fill", "-f", "--draft", "-d"},
    },
    ("issue", "view"): {
        "value": {"--json", "--jq", "-q"},
        "bool": {"--comments", "-c"},
    },
    ("pr", "view"): {
        "value": {"--json", "--jq", "-q"},
        "bool": {"--comments", "-c"},
    },
    ("pr", "diff"): {
        "value": {"--color"},
        "bool": set(),
    },
    ("pr", "checks"): {
        "value": set(),
        "bool": set(),
    },
    ("pr", "comment"): {
        "value": {"--body", "-b", "--body-file", "-F"},
        "bool": set(),
    },
    ("pr", "review"): {
        "value": {"--body", "-b"},
        "bool": {"--approve", "-a", "--request-changes", "-r", "--comment", "-c"},
    },
    ("pr", "merge"): {
        # 第2次修正（オーナー確定 2026-07-15）: `--admin`（ブランチ保護バイパス）を除外。将来ブランチ
        # 保護を有効化したとき pr-reviewer が「レビュー経由でのみ merge」不変条件を破る余地を最小権限で塞ぐ。
        "value": set(),
        "bool": {"--squash", "-s", "--merge", "-m", "--rebase", "-r", "--delete-branch", "-d"},
    },
    ("pr", "checkout"): {
        "value": set(),
        "bool": set(),
    },
}

# 層1（Issue #227）: クォート外で禁止する記号。パイプ `|`・バックグラウンド/fd複製 `&`・チェイン `;`・
# サブシェル `( )`・ブレース展開 `{ }`・リダイレクト/ヒアドキュメント/here-string `< >`・
# コマンド置換 `$` backtick・改行（複数行＝複数コマンド）。これらを記号レベルで締め出すことで、
# #189〜#222 の40件超のバイパス（すべてこれらの記号を悪用する）を個別列挙なしに一括で塞ぐ。
# ブレース `{ }` は bash がトークン化後に展開するため（`git m{e..e}rge`→`git merge`・
# `git {merge,status}`→2語）、shlex ベースの層3 判定と bash 実行が乖離してバイパスになる（Issue #227
# レビュー F1）。`( ) | $` 等と同じくクォート外で一律 deny することで構造的に塞ぐ。
DANGEROUS_UNQUOTED_CHARS = set("|&;(){}<>$`\n")
# ダブルクォート内で禁止する記号。展開が有効なのは `$`（変数展開・コマンド置換・算術展開）と
# backtick（コマンド置換）だけで、`( ) | ; < > &` はリテラル。よってダブルクォート内の丸括弧は許可する
# （`gh pr create --title "fix(hooks): ..."` の over-deny 防止＝Issue #227 の必須要件）。
DANGEROUS_DOUBLE_QUOTED_CHARS = set("$`")

# 層2（Issue #227）: 先頭語ホワイトリスト。ここに無い先頭語は一律 deny（列挙不要）。
ALLOWED_HEAD_COMMANDS = {"git", "gh"}
PYTHON_HEAD_COMMANDS = {"python", "python3"}
# python は「モジュール実行（-m）で、かつ以下のモジュール」に限る（オーナー確定）。
# `python3 -c ...`・素の `python3 script.py`・その他のモジュールは deny。
# 第2次修正（オーナー確定 2026-07-15）: pytest は任意 path/conftest/plugin を実行する構造で絞れないため
# 除外（この repo は unittest 方針・CLAUDE.md）。coverage は run を禁止し report/html/xml/json のみ許可
# （`coverage run <なんでも>` は任意 Python 実行経路のため）。「-c 禁止したのに coverage run 素通し」の
# 不整合を消し、エージェントの混乱・ハルシネーションリスクを下げる（防御力は #129 限界のため不変）。
ALLOWED_PYTHON_MODULES = {"unittest", "coverage", "dsv2", "gitgate"}
# ロール別の**追加**モジュール（Issue #308）。基底集合 ALLOWED_PYTHON_MODULES に上乗せする形でのみ
# 使い、基底から差し引く用途には使わない（絞りたくなったら基底側を直す）。
#
# `karte` を issue-fixer にだけ足すのは、カルテ（`tmp/_karte/issue-<N>.md`）の**書き手を
# issue-fixer に一本化する**という Issue #308 の設計をここでも機械的に担保するため。
# `python3 -m karte append` はカルテへの追記＝ループ状態の書き換えなので、基底集合に入れて
# 全 gated ロールへ配ると pr-reviewer（read-only・Write 非付与が fail-close の保証）にまで
# 書込経路が生えてしまう。`karte` 自体は argparse の固定 CLI で任意コード実行経路を持たず、
# 書き先も repo-root 配下の `tmp/_karte/` に fail-close で限定されている（`karte/paths.py`）ため、
# issue-fixer に限れば `dsv2` と同格の「コーパス操作ツール」として扱える。
PYTHON_MODULES_BY_ROLE = {
    "issue-fixer": {"karte"},
}
# `karte` は**状態を書き換える verb を持つ**ため、モジュール単位ではなく verb 単位で絞る
# （Issue #341 レビュー F-341-04）。`coverage` の `run` を禁じているのと同じ方式。
#
# **`ingest-review` を issue-fixer に許さない**のが要点：これは「レビューアの指摘を台帳へ取り込む」
# 手続きで、`status: resolved` を書ける。是正当事者がこれを実行できると、自作のレポートを `--from` で
# 食わせて未解消 finding を一括 resolved にし round を進められ、`append` の類似飽和拒否
# （#307 が入れたループ遮断）を迂回できてしまう＝「指摘した側」と「直す側」の分離が壊れる。
# 取り込みは主文脈（gated ロールではない）が行う。
KARTE_ALLOWED_SUBCOMMANDS = {"render", "append", "close-attempt", "check", "status"}
# coverage は実行系サブコマンド（run）を禁止し、レポート出力系のみ許可する。
COVERAGE_ALLOWED_SUBCOMMANDS = {"report", "html", "xml", "json"}


def allowed_python_modules(role):
    """層2 の python モジュール許可集合（基底＋ロール別の追加分）。"""
    return ALLOWED_PYTHON_MODULES | PYTHON_MODULES_BY_ROLE.get(role, set())

# 全 agent_type 共通の危険コマンド deny 層（Issue #224 フォローアップ・案B）。settings.json の
# permissions.deny が env-prefix/abspath/compound で機械的にすり抜けるため、この hook 側で補完する。
NETWORK_COMMANDS = {
    "curl", "wget", "nc", "ncat", "netcat", "socat", "telnet",
    "ftp", "tftp", "ssh", "scp", "sftp", "rsync",
}
SHELL_INTERPRETERS = {"bash", "sh", "zsh", "dash"}
SCRIPT_EVAL_INTERPRETERS = {"perl", "ruby", "node"}
# eval/source は任意トークン一致で deny する（`true & eval x` 等の非先頭位置も捕捉）。`.`（dot-source）
# だけは**コマンド位置のみ**判定する（PR #237 修正で任意トークン一致にすると `git add .`・`grep x .`
# のカレントディレクトリ引数まで over-deny してしまう有害な over-match を避けるための意図的な線引き）。
EVAL_SOURCE_COMMANDS = {"eval", "source"}
DOT_SOURCE_COMMAND = "."
# quote-aware ではない素朴なセグメント分割（`;`/`&&`/`||`/`|`/`(`/`)`/改行/`$(`/backtick）。
# クォート内の記号でも分割されるが、その結果生じる断片はクォート対応が崩れて shell_words での
# トークン化に失敗し読み飛ばされる（fail-open・over-match 回避が狙い。詳細はファイル冒頭コメント）。
SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||[;|\n()]|\$\(|`")


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def redact(value):
    if isinstance(value, dict):
        return {
            key: ("<redacted>" if SENSITIVE_KEY_RE.search(str(key)) else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def debug_payload(payload, decision, reason):
    path = os.environ.get("AGENT_COMMAND_GATE_DEBUG_PAYLOAD")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "payload": redact(payload),
                "decision": decision,
                "reason": reason,
            }, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass


# 常時有効の最小トレース（Issue #192・.codex 版と同じ設計）：AGENT_COMMAND_GATE_DEBUG_PAYLOAD
# （オプトイン・フルペイロード・デフォルト無効）とは別に、"フックが実際に呼ばれたか" だけを常時
# 1行追記で残す。command 本文や生 payload は含めない（機微情報を持たない設計）。既定パスは
# AGENT_COMMAND_GATE_TRACE_LOG で上書きでき、空文字を設定すると無効化できる（テストや no-op 運用向け）。
TRACE_DEFAULT_PATH = os.path.expanduser("~/.claude/agent-command-gate-trace.log")
TRACE_MAX_BYTES = 1_000_000  # 超過したら1世代だけ .1 にローテートする（際限ない肥大化を防ぐ）。


def trace_event(agent_type, tool_name, decision):
    path = os.environ.get("AGENT_COMMAND_GATE_TRACE_LOG", TRACE_DEFAULT_PATH)
    if not path:
        return
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        try:
            if os.path.getsize(path) > TRACE_MAX_BYTES:
                os.replace(path, path + ".1")
        except OSError:
            pass
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "agent_type": agent_type or None,
                "tool_name": tool_name or None,
                "decision": decision,
            }, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass


# Issue #340（#308 実装中に実踏）: このフックは末尾で必ず `exit 0` する。よって埋め込み Python が
# 未捕捉例外で落ちると **stdout が空のまま終わり、呼び出し側からは allow と区別が付かない**
# ＝内部エラーがそのまま権限ゲートの素通しに化ける。「検査できないものは deny する」という本フックの
# 他の判断（payload 破損・トークン化失敗・未知 MCP ツール）と揃えるため、未捕捉例外も deny に落とす。
# try/except ではなく excepthook で受けるのは、既存の判定ロジックを**再インデントせずに**全体を
# 覆えるため（数百行を囲うと diff が本質の変更を埋めてレビュー不能になる）。
# 注意: これは `GATED_ROLES` 外ロールの fail-open（2026-07-11 オーナー確定・ヘッダ参照）とは別物。
# あちらは「判定した上で許可する」設計判断、こちらは「判定しようとして落ちた」場合の話。
def deny_on_internal_error(exc_type, exc_value, _traceback):
    deny(
        f"agent-command-gate: the gate itself failed with {exc_type.__name__}: {exc_value}; "
        "refusing because the command could not be inspected. This is a bug in the hook, "
        "not in the command."
    )
    try:
        trace_event(None, None, "deny")
    except Exception:
        pass


sys.excepthook = deny_on_internal_error

# Issue #340: gated ロールは**ロール別 dict すべて**に登録されていなければならない。1つでも
# 欠けると該当ロールの判定が KeyError で落ちる（#308 で `GATED_ROLES` にだけ足して踏んだ）。
# 上の excepthook があれば deny に倒れるが、それは「壊れたまま止まる」であって正しい状態ではない
# ので、発生源で fail-close する。`PYTHON_MODULES_BY_ROLE` は**意図的に一部ロールだけ**を持つ
# 上乗せ表（既定は基底集合）なので、この全ロール必須の検査には含めない。
missing_role_tables = {}
for gated_role in sorted(GATED_ROLES):
    absent = [
        table_name
        for table_name, table in (
            ("GITGATE_VERBS_BY_ROLE", GITGATE_VERBS_BY_ROLE),
            ("GH_SUBCOMMANDS_BY_ROLE", GH_SUBCOMMANDS_BY_ROLE),
        )
        if gated_role not in table
    ]
    if absent:
        missing_role_tables[gated_role] = absent
if missing_role_tables:
    raise RuntimeError(
        "gated role(s) are not registered in every role table: "
        + "; ".join(
            f"{gated_role} missing from {', '.join(tables)}"
            for gated_role, tables in sorted(missing_role_tables.items())
        )
        + ". Register the role in every table (or drop it from GATED_ROLES)."
    )


try:
    with open(sys.argv[1]) as f:
        payload = json.load(f)
except Exception:
    deny("agent-command-gate: PreToolUse payload is not valid JSON; refusing because the Bash command cannot be inspected.")
    trace_event(None, None, "deny")
    sys.exit(0)


def first_string(*values):
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


agent_type = first_string(
    payload.get("agent_type"),
    payload.get("subagent_type"),
    (payload.get("agent") or {}).get("type") if isinstance(payload.get("agent"), dict) else None,
)
# tool_name は Bash 経路では判定に使わない（settings.json の matcher:"Bash" で既に絞り込み済み）が、
# Issue #303 以降は **MCP 経路の識別に使う**——`mcp__` 始まりなら実行系 MCP ツールとして
# 別入口（ctx_gate_reason）へ振る。tool_name 欠如は従来どおり Bash 扱い（既存テストとの互換）。
tool_name = first_string(payload.get("tool_name"))
tool_input = payload.get("tool_input")
command = tool_input.get("command") if isinstance(tool_input, dict) else None


def dangerous_shell_symbol(command_text):
    """層1: コマンド文字列をクォート状態を追いながら1文字ずつ走査し、最初に見つかった危険記号の
    説明文字列を返す（危険記号が無ければ None）。

    状態は normal（クォート外）／single（'…'）／double（"…"）の3つ。
      - normal: DANGEROUS_UNQUOTED_CHARS（`| & ; ( ) < > $ backtick 改行`）を見つけたら deny。
      - double: DANGEROUS_DOUBLE_QUOTED_CHARS（`$` backtick）のみ deny。それ以外（丸括弧・パイプ・
        セミコロン等）はダブルクォート内ではリテラルであり、実際にコマンドを起動しないため許可する。
      - single: シングルクォート内は全てリテラルで、シングルクォートからは脱出できない（bash 仕様）。
        よって走査不要（閉じ引用符だけを探す）。

    バックスラッシュのエスケープを正しく追うことは必須（安全性の要）。素朴に無視すると
    `git \\' ; git merge evil ; \\'` のような入力で、bash は `\\'` をリテラルのクォート文字として
    扱う（＝クォートは開かない・`;` はトップレベルのコマンド境界）のに対し、スキャナ側は `'` を
    クォート開始と誤認して以降の `;` を「シングルクォート内のリテラル」とみなし、見逃しになる。
    normal/double のどちらでもバックスラッシュは次の1文字をリテラル化するものとして消費する
    （bash と同じ扱い＝`"\\$(x)"` はコマンド置換にならない一方で `"\\\\$(x)"` はなる、を正しく判定できる）。
    行継続（`\\` + 改行）・末尾の裸のバックスラッシュ・閉じられていないクォートは「検査不能」として deny する
    （安全側）。
    """
    state = "normal"
    index = 0
    length = len(command_text)
    while index < length:
        char = command_text[index]
        if state == "normal":
            if char == "\\":
                if index + 1 >= length:
                    return "a trailing backslash (incomplete escape; the command cannot be inspected)"
                if command_text[index + 1] == "\n":
                    return "a line continuation (backslash + newline; only single-line commands are allowed)"
                index += 2  # エスケープされた1文字はリテラル（bash と同じ）
                continue
            if char == "'":
                state = "single"
                index += 1
                continue
            if char == '"':
                state = "double"
                index += 1
                continue
            if char in DANGEROUS_UNQUOTED_CHARS:
                return describe_symbol(char, "outside quotes")
            index += 1
            continue
        if state == "single":
            if char == "'":
                state = "normal"
            index += 1
            continue
        # state == "double"
        if char == "\\":
            if index + 1 >= length:
                return "a trailing backslash (incomplete escape; the command cannot be inspected)"
            index += 2  # ダブルクォート内でも `\\$`/`\\backtick` はリテラル化される
            continue
        if char == '"':
            state = "normal"
            index += 1
            continue
        if char in DANGEROUS_DOUBLE_QUOTED_CHARS:
            return describe_symbol(char, "inside double quotes")
        index += 1
    if state != "normal":
        return "an unterminated quote (the command cannot be inspected)"
    return None


SYMBOL_LABELS = {
    "|": "a pipe `|`",
    "&": "an `&` (background / fd duplication)",
    ";": "a command separator `;`",
    "(": "a subshell `(`",
    ")": "a subshell `)`",
    "{": "a brace expansion `{`",
    "}": "a brace expansion `}`",
    "<": "a redirection / heredoc `<`",
    ">": "a redirection `>`",
    "$": "an expansion / command substitution `$`",
    "`": "a command substitution backtick",
    "\n": "a newline (multiple commands)",
}


def describe_symbol(char, where):
    return f"{SYMBOL_LABELS.get(char, repr(char))} {where}"


def strip_wrappers_or_env_reason(tokens):
    """層3 の前処理（gated ロールのみ）。`rtk`/`command`/`builtin`/`exec` の純ラッパーは剥がして
    内側を再検査する。ただし先頭の環境変数代入（`NAME=value`）と `env` ラッパーは deny する
    （`GIT_SSH_COMMAND=`/`PATH=`/`GIT_EXTERNAL_DIFF=` 等の env 経由 config/挙動注入に正当理由がない
    ため。オーナー原則「config/alias/global-option/env 代入は一律 deny」の一部）。
    返り値は (剥がした後の tokens, deny 理由 or None)。deny 理由が非 None のとき tokens は None。"""
    tokens = list(tokens)
    while tokens:
        head = tokens[0]
        if ASSIGNMENT_RE.match(head):
            return None, "a leading environment-variable assignment (`NAME=value`); env-based config/behavior injection is not allowed for this role"
        if head == "env":
            return None, "an `env` wrapper; env-based config/behavior injection is not allowed for this role"
        if head in WRAPPER_COMMANDS:
            tokens.pop(0)
            continue
        break
    return tokens, None


def shell_words(command_text):
    """コマンド文字列を単語列に分解する。分解できない（クォートの対応が取れない等）場合は None を
    返し、呼び出し側が「検査不能＝deny」に倒す（層1で既に弾かれるはずだが fail-close を二重化する）。"""
    try:
        return shlex.split(command_text, posix=True)
    except ValueError:
        return None


def strip_leading_wrappers(tokens):
    """全 agent_type 共通の危険コマンド層（Issue #224 フォローアップ）の前処理。層3専用の
    strip_wrappers_or_env_reason と異なり、env 代入・`env` ラッパー自体を deny 理由にはしない
    （env 代入は agent_type を問わず一般的に許可された用法であり、本層は「その先の実効コマンドが
    危険かどうか」だけを見る）。先頭の環境変数代入（`NAME=value`）・`env` ラッパー（直後のフラグ／
    代入も簡易的にスキップする）・rtk/command/builtin/exec の純ラッパーを剥がした tokens を返す。"""
    tokens = list(tokens)
    while tokens:
        head = tokens[0]
        if ASSIGNMENT_RE.match(head):
            tokens.pop(0)
            continue
        if head == "env":
            tokens.pop(0)
            while tokens and (ASSIGNMENT_RE.match(tokens[0]) or tokens[0].startswith("-")):
                tokens.pop(0)
            continue
        if head in WRAPPER_COMMANDS:
            tokens.pop(0)
            continue
        break
    return tokens


def segment_dangerous_command_token(segment_tokens):
    """1セグメント分の tokens を判定する。危険なら表示用文字列を、問題なければ None を返す。
    パス付き（`/usr/bin/curl` 等）も os.path.basename で正規化して判定する（絶対パスによるすり抜けを
    防ぐ・Issue #224）。

    PR #237 critical 修正: **先頭語のみ**の判定は `timeout 5 curl x`・`nice curl x`・`nohup curl x`・
    `xargs curl x`・`echo x & curl y`・`{ curl z; }`・`sudo curl x`・`env FOO=1 curl x` のように危険
    コマンドを非先頭トークンに置くだけで記号ゼロで deny をすり抜けた（#227 が脱却した denylist いたち
    ごっこの再来）。よって NETWORK/インタプリタ/eval・source は**セグメント内の全独立トークン**を走査
    する（オーナー承認済み「独立トークン一致」）。トークン一致なので、クォートで1トークンになった
    文字列（`git commit -m "fix curl bug"` の `fix curl bug`・`echo "see curl docs"`）や部分文字列
    （`python3 test_curl.py` の `test_curl.py`）は巻き込まない。"""
    if not segment_tokens:
        return None
    basenames = [os.path.basename(token) for token in segment_tokens]
    # ネットワークコマンド: いずれかの独立トークンが一致すれば deny（wrapper 経由 `timeout curl` 等を含む）。
    for name in basenames:
        if name in NETWORK_COMMANDS:
            return name
    # インタプリタの任意実行: インタプリタ名トークンと対応フラグトークンが同一セグメント内に共存すれば
    # deny（`xargs bash -c '{}'`・`timeout python3 -c '...'` 等の wrapper 経由も捕捉する）。
    # `python3 -m <module>` は `-c` トークンを持たないため allow を厳守する（オーナー確定）。
    has_c = "-c" in segment_tokens
    has_e = "-e" in segment_tokens
    if has_c:
        for name in basenames:
            if name in SHELL_INTERPRETERS or name in PYTHON_HEAD_COMMANDS:
                return f"{name} -c"
    if has_e:
        for name in basenames:
            if name in SCRIPT_EVAL_INTERPRETERS:
                return f"{name} -e"
    # eval/source: いずれかの独立トークンが一致すれば deny（`true & eval x` 等の非先頭位置も捕捉）。
    for name in basenames:
        if name in EVAL_SOURCE_COMMANDS:
            return name
    # `.`（dot-source）だけはコマンド位置（純ラッパー剥がし後の先頭語）でのみ判定する。任意トークン
    # 一致にすると `git add .`・`grep x .` 等のカレントディレクトリ引数まで over-deny してしまうため
    # （PR #237 修正で新たに生じ得た有害な over-match を避ける意図的な線引き）。
    stripped = strip_leading_wrappers(segment_tokens)
    if stripped and os.path.basename(stripped[0]) == DOT_SOURCE_COMMAND:
        return DOT_SOURCE_COMMAND
    return None


def all_role_dangerous_command_token(command_text):
    """全 agent_type 共通の危険コマンド層（Issue #224 フォローアップ・案B）。command_text を
    SEGMENT_SPLIT_RE でセグメント分割し、各セグメントの全独立トークン（basename 正規化）が
    NETWORK_COMMANDS・インタプリタ任意実行フォーム・eval/source/. に該当すれば表示用トークンを返す。
    セグメントがトークン化できない場合（クォートが分割で崩れた断片等）は検査不能として読み飛ばす
    （fail-open・over-match を避けるため。ファイル冒頭コメント参照）。問題が無ければ None を返す。"""
    for raw_segment in SEGMENT_SPLIT_RE.split(command_text):
        segment = raw_segment.strip()
        if not segment:
            continue
        tokens = shell_words(segment)
        if not tokens:
            continue
        token = segment_dangerous_command_token(tokens)
        if token:
            return token
    return None


def head_command_violation(tokens, role):
    """層2: 先頭語ホワイトリスト。許可なら None、違反ならその説明を返す。
    パス付き（`/usr/bin/git`・`./git`）は完全一致しないため deny（カレントディレクトリに `git` という
    名前のスクリプトを置いて実行する迂回を防ぐ＝basename 判定にはしない）。
    python モジュールの許可集合は**ロール別**（基底＋追加分・Issue #308）。"""
    head = tokens[0]
    allowed_modules = allowed_python_modules(role)
    if head in ALLOWED_HEAD_COMMANDS:
        return None
    if head in PYTHON_HEAD_COMMANDS:
        modules = "|".join(sorted(allowed_modules))
        if len(tokens) >= 3 and tokens[1] == "-m" and tokens[2] in allowed_modules:
            # 第2次修正: coverage は run（任意 Python 実行）を禁止し、レポート出力系のみ許可する。
            if tokens[2] == "coverage":
                subcommand = tokens[3] if len(tokens) >= 4 else ""
                if subcommand not in COVERAGE_ALLOWED_SUBCOMMANDS:
                    subs = "|".join(sorted(COVERAGE_ALLOWED_SUBCOMMANDS))
                    return (
                        f"`python3 -m coverage` only allows the report subcommands "
                        f"<{subs}> (`coverage run <...>` executes arbitrary Python and is denied)"
                    )
            # Issue #341 F-341-04: karte は verb 単位で絞る（ingest-review は是正ロールに許さない）。
            if tokens[2] == "karte":
                subcommand = tokens[3] if len(tokens) >= 4 else ""
                if subcommand not in KARTE_ALLOWED_SUBCOMMANDS:
                    subs = "|".join(sorted(KARTE_ALLOWED_SUBCOMMANDS))
                    return (
                        f"`python3 -m karte` only allows <{subs}> for this role "
                        "(`ingest-review` writes finding status and belongs to the reviewing side, "
                        "not to the role being reviewed)"
                    )
            return None
        return (
            f"`{head}` is only allowed in the form `{head} -m <{modules}> ...` "
            f"(`-c`, bare scripts and other modules are denied)"
        )
    return (
        f"`{head}` is not in the allowed command whitelist "
        f"(git, gh, python3 -m <{'|'.join(sorted(allowed_modules))}>)"
    )


def raw_git_denied_reason(role):
    """層3(git): gated ロールは生 git を一切使えない（Issue #227 追加修正3）。git 操作は固定
    テンプレートの `python3 -m gitgate <verb>` ラッパー経由に限る（ユーザ制御フラグが git に届かない）。"""
    return (
        "raw `git` is not allowed for this role; use `python3 -m gitgate <verb>` instead "
        "(the gitgate wrapper builds a fixed git command, so user-controlled flags such as "
        "`--receive-pack`/`--upload-pack`/`--output` never reach git). Verbs allowed for this role: "
        + ", ".join(sorted(GITGATE_VERBS_BY_ROLE[role]))
    )


def gitgate_violation(tokens, role):
    """層3(gitgate): `python3 -m gitgate <verb> …` の verb をロール別集合で判定する。層2 で
    tokens[2]=='gitgate' の形が保証されている。許可なら None、違反なら理由文字列を返す。"""
    verb = tokens[3] if len(tokens) >= 4 else ""
    if verb not in GITGATE_VERBS_BY_ROLE[role]:
        allowed = ", ".join(sorted(GITGATE_VERBS_BY_ROLE[role]))
        return (
            f"`gitgate {verb}`".rstrip()
            + f" is not in this role's gitgate verb allowlist ({allowed})"
        )
    return None


def gh_key_and_rest(tokens):
    """gh のサブコマンドキーと、その後続トークン（フラグ・位置引数）を返す。tokens[0]=='gh' 前提。
    先頭 global option は `--repo <val>`/`-R <val>`/`--repo=<val>`/`-R<val>` の値スキップのみ許容し、
    それ以外の先頭 `-*` があれば (None, 理由文字列) を返す（呼び出し側で deny）。
    返り値: ((subcommand,) または (subcommand, subsubcommand), rest_tokens)。pr/issue は第2 bare
    トークンを subsub とし、rest はそれ以降のトークン列。"""
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in {"--repo", "-R"} and index + 1 < len(tokens):
            index += 2
            continue
        if token.startswith("--repo=") or (token.startswith("-R") and len(token) > 2):
            index += 1
            continue
        if token.startswith("-"):
            return None, (
                "a gh global option other than `--repo`/`-R`; "
                "other global options are not allowed for this role"
            )
        break
    if index >= len(tokens):
        return ("",), []
    subcommand = tokens[index]
    if subcommand in {"pr", "issue"}:
        if index + 1 < len(tokens) and not tokens[index + 1].startswith("-"):
            return (subcommand, tokens[index + 1]), tokens[index + 2:]
        return (subcommand, ""), tokens[index + 1:]
    return (subcommand,), tokens[index + 1:]


def gh_flag_violation(key, rest):
    """層3(gh): key（(sub,subsub)）の許可フラグ集合に照らして rest（後続トークン）を検査する。
    許可なら None、未知/禁止フラグがあれば理由文字列を返す。value フラグは次トークン（または `=`/
    連結）を値として消費し、bool フラグは値を取らない。位置引数（PR/issue 番号等）は自由。
    `--web`/`--editor` 等は許可集合に無いため deny される。"""
    spec = GH_FLAG_ALLOWLIST.get(key, {"value": set(), "bool": set()})
    value_flags = spec["value"] | GH_COMMON_VALUE_FLAGS
    bool_flags = spec["bool"]
    label = "gh " + " ".join(key)
    index = 0
    while index < len(rest):
        token = rest[index]
        if token == "--":
            break  # 以降はすべて位置引数
        if token.startswith("--"):
            name = token.split("=", 1)[0]
            has_eq = "=" in token
            if name in value_flags:
                index += 1 if has_eq else 2
                continue
            if name in bool_flags:
                index += 1
                continue
            return f"`{label}` does not allow the flag `{name}` (unknown or forbidden flag)"
        if token.startswith("-") and len(token) >= 2:
            short = token[:2]
            attached = token[2:]
            if short in value_flags:
                index += 1 if attached else 2
                continue
            if short in bool_flags:
                if attached:
                    return f"`{label}` does not allow `{token}` (combined short flags are not permitted)"
                index += 1
                continue
            return f"`{label}` does not allow the flag `{short}` (unknown or forbidden flag)"
        index += 1  # 位置引数
    return None


def gh_violation(tokens, role):
    """層3(gh): ロール別の許可サブコマンド＋フラグ判定。許可なら None、違反なら理由文字列を返す。"""
    key, rest = gh_key_and_rest(tokens)
    if key is None:
        return rest  # rest は理由文字列（gh_key_and_rest の global-option 違反）
    if key not in GH_SUBCOMMANDS_BY_ROLE[role]:
        allowed = ", ".join("gh " + " ".join(k) for k in sorted(GH_SUBCOMMANDS_BY_ROLE[role]))
        return f"`gh {' '.join(key).rstrip()}` is not in this role's gh allowlist ({allowed})"
    return gh_flag_violation(key, rest)


def role_command_violation(tokens, role):
    """層3: ロール別許可判定。層1・層2 を通過した時点で tokens は「記号を含まない単純な1コマンド」かつ
    先頭語は git/gh/python -m <module> のいずれか。git は生実行を deny（gitgate ラッパー経由に誘導）、
    gh はサブコマンド＋フラグ許可リスト、python -m gitgate は verb をロール別集合で判定する。
    その他の python モジュール（unittest 等）は層2 で許可済みでここでは制限しない。"""
    head = tokens[0]
    if head == "git":
        return raw_git_denied_reason(role)
    if head == "gh":
        return gh_violation(tokens, role)
    if head in PYTHON_HEAD_COMMANDS and len(tokens) >= 3 and tokens[1] == "-m" and tokens[2] == "gitgate":
        return gitgate_violation(tokens, role)
    return None


def gate_reason(command_text, role):
    """3層すべてを通し、deny する場合は理由文字列を、許可する場合は None を返す。"""
    symbol = dangerous_shell_symbol(command_text)
    if symbol:
        return (
            f"agent-command-gate ({role}): the command contains {symbol}. "
            "This role may only run a single simple command with no shell metacharacters "
            "(no pipes, subshells, command substitution, redirection, heredocs, chaining or newlines). "
            "Write bodies to a file with the Write tool and pass them via `python3 -m gitgate commit <file>` / "
            "`gh pr create --body-file <file>` / `gh pr comment --body-file <file>`; use native flags "
            "(`gh --jq`, `python3 -m gitgate log --grep <pat> -n <N>`) and the Read/Grep/Glob tools instead of pipes."
        )
    tokens = shell_words(command_text)
    if tokens is None:
        return (
            f"agent-command-gate ({role}): the command cannot be tokenized (unbalanced quotes); "
            "refusing because it cannot be inspected."
        )
    tokens, env_reason = strip_wrappers_or_env_reason(tokens)
    if env_reason:
        return (
            f"agent-command-gate ({role}): the command starts with {env_reason} "
            "(Issue #227: config/alias, git/gh global options and env assignments are denied for this role)."
        )
    if not tokens:
        return (
            f"agent-command-gate ({role}): no command word could be found; "
            "refusing because the command cannot be inspected."
        )
    head_violation = head_command_violation(tokens, role)
    if head_violation:
        modules = "|".join(sorted(allowed_python_modules(role)))
        return (
            f"agent-command-gate ({role}): {head_violation}. "
            f"Only git / gh / python3 -m <{modules}> are allowed for this role "
            "(whitelist mode, Issue #227). Use the Read/Grep/Glob/Write tools for file work."
        )
    violation = role_command_violation(tokens, role)
    if violation:
        return (
            f"agent-command-gate ({role}): {violation}. "
            "Layer 3 (Issue #227) forbids raw git (use `python3 -m gitgate <verb>`) and allows only "
            "this role's gitgate verbs and gh subcommands/flags; config/alias, git/gh global options, "
            "env assignments and cross-role actions (issue-implementer/issue-fixer merging, pr-reviewer pushing) are denied."
        )
    return None


def ctx_tool_suffix(name):
    """tool_name（`mcp__<server>__<tool>`）から末尾のツール名を取り出す。"""
    return name.rsplit("__", 1)[-1] if name else ""


def ctx_commands_or_reason(suffix, tool_input_obj):
    """Issue #303: 実行系 MCP ツールの入力を「シェルコマンド文字列のリスト」へ正規化する。

    戻り値は (commands, reason)。reason が非 None のとき deny（commands は None）。

    **fail-close**: 形が読めない／未知言語／未知ツールは **全 agent_type で deny** する。
    Bash 経路の非ゲートロールは command 欠落でも許可する（既存ワークフロー救済・不変条件#1）が、
    ここは意図的に非対称にしている——新規に統制下へ入れるツールには救済すべき既存ワークフローが
    無く、「検査できないものを通す」既定を新設する理由がないため。
    """
    if not isinstance(tool_input_obj, dict):
        return None, "the MCP tool_input is not an object; refusing because the code cannot be inspected"

    if suffix == "ctx_batch_execute":
        entries = tool_input_obj.get("commands")
        if not isinstance(entries, list) or not entries:
            return None, (
                "`ctx_batch_execute` requires a non-empty `commands` array; "
                "refusing because the commands cannot be inspected"
            )
        commands = []
        for entry in entries:
            if not isinstance(entry, dict):
                return None, (
                    "every `ctx_batch_execute` entry must be an object with a `command` string; "
                    "refusing because the commands cannot be inspected"
                )
            value = entry.get("command")
            if not isinstance(value, str) or not value:
                return None, (
                    "every `ctx_batch_execute` entry must carry a non-empty `command` string; "
                    "refusing because the commands cannot be inspected"
                )
            commands.append(value)
        return commands, None

    # ctx_execute / ctx_execute_file
    language = tool_input_obj.get("language")
    if not isinstance(language, str) or language not in CTX_ALLOWED_LANGUAGES:
        allowed = "|".join(sorted(CTX_ALLOWED_LANGUAGES))
        return None, (
            f"`{suffix}` is only allowed with language={allowed}; `language={language!r}` runs an "
            "interpreter over arbitrary source, which is equivalent to `python3 -c` / `node -e` and is "
            "already denied for every agent_type (Issue #224/#303). Non-shell code cannot be inspected "
            "statically, so the language itself is allowlisted instead"
        )
    code = tool_input_obj.get("code")
    if not isinstance(code, str) or not code:
        return None, (
            f"`{suffix}` requires a non-empty `code` string; refusing because it cannot be inspected"
        )
    return [code], None


def ctx_gate_reason(suffix, tool_input_obj, role):
    """実行系 MCP ツールの判定入口。正規化した各コマンド文字列を、Bash とまったく同じ
    universal 層（全 agent_type）＋層1〜3（gated ロールのみ）へ通す。判定ロジックは
    `all_role_dangerous_command_token()` / `gate_reason()` の再利用で、新規実装はしない。"""
    if suffix not in CTX_EXEC_TOOL_SUFFIXES:
        # matcher の取りこぼし・プラグイン側の名称変更・将来の MCP ツール追加は allowlist 外＝deny。
        # 「matcher だけ広げてパース未対応」が素通しではなく deny に倒れる（Issue #269 の allowlist 原則）。
        allowed = ", ".join(sorted(CTX_EXEC_TOOL_SUFFIXES))
        return (
            f"agent-command-gate: MCP tool '{suffix}' is not in this hook's inspected allowlist "
            f"({allowed}); refusing (fail-close, Issue #269/#303)."
        )

    commands, parse_reason = ctx_commands_or_reason(suffix, tool_input_obj)
    if parse_reason:
        return f"agent-command-gate ({role or 'no-agent-type'}): {parse_reason}."

    # `cwd` は context-mode 自身が「未指定のときだけプロジェクトルートを補う」動作なので、
    # 明示されている＝モデルが別ディレクトリを狙った場合だけを見ればよい（フックの実行順に依存しない）。
    # gated ロールがリポジトリ外で実行すると、push/merge の非対称が掛かる対象そのものを差し替えられる。
    if role in GATED_ROLES:
        cwd = tool_input_obj.get("cwd")
        if cwd is not None:
            return (
                f"agent-command-gate ({role}): an explicit `cwd` is not allowed for this role "
                "(running outside the project root escapes the repo-scoped push/merge boundary). "
                "Omit `cwd` — context-mode pins it to the project root on its own."
            )

    # 1件でも違反があれば呼び出し全体を deny する（部分許可はハーネス側に表現手段がない）。
    for command_text in commands:
        token = all_role_dangerous_command_token(command_text)
        if token:
            return (
                f"agent-command-gate: '{token}' is a denied network/exec command for all roles "
                f"(reached via {suffix}; Issue #224/#303)."
            )
        if role in GATED_ROLES:
            violation = gate_reason(command_text, role)
            if violation:
                return violation
    return None


is_mcp = bool(tool_name) and tool_name.startswith("mcp__")

dangerous_token = None
if not is_mcp and isinstance(command, str) and command:
    dangerous_token = all_role_dangerous_command_token(command)

reason = None
if is_mcp:
    # Issue #303: 実行系 MCP 経路。tool_input の形が Bash と違う（`code`+`language` /
    # `commands[]`）ため専用入口で正規化してから、同じ判定関数へ通す。
    reason = ctx_gate_reason(ctx_tool_suffix(tool_name), tool_input, agent_type)
elif dangerous_token:
    # 全 agent_type 共通の危険コマンド層（Issue #224 フォローアップ・案B）。対象ロール専用の層1〜3
    # より前に判定し、agent_type を問わず deny する（main context 自身・各 *-author 等の従来「常に許可」
    # だった穴を、settings.json permissions.deny では塞ぎ切れない env-prefix/abspath/compound 経路について
    # 補完する）。
    reason = (
        f"agent-command-gate: '{dangerous_token}' is a denied network/exec command for all roles "
        "(Issue #224 env-prefix/abspath guard: settings.json permissions.deny is a static prefix match "
        "that env-var prefixes / absolute paths / compound commands can bypass, so this hook denies it "
        "independent of agent_type)."
    )
elif agent_type not in GATED_ROLES:
    # agent_type が対象ロール以外（欠如を含む・main context 自身がこれに該当）はロール専用判定
    # （層1〜3）の対象外＝常に許可（ヘッダのオーナー判断・不変条件#1）。command 欠落でも許可する
    # （Codex 版と dispatch 順を統一・Issue #227 レビュー F3。対象ロールについては下で command 欠落→deny
    # を維持）。危険コマンドは上の全 agent_type 共通層で既に deny 済み。
    pass
elif not isinstance(command, str) or not command:
    reason = "agent-command-gate: PreToolUse payload does not contain tool_input.command; refusing because the Bash command cannot be inspected."
else:
    reason = gate_reason(command, agent_type)

if reason:
    debug_payload(payload, "deny", reason)
    trace_event(agent_type, tool_name, "deny")
    deny(reason)
else:
    debug_payload(payload, "allow", "")
    trace_event(agent_type, tool_name, "allow")
PYEOF
gate_status=$?
gate_stdout="$(cat "$gate_out")"

# Issue #341 F-341-08: 埋め込み Python の `sys.excepthook`（#340）は**実行時例外しか捕まえられない**。
# 構文エラー（フック編集時にごく普通に起こる）ではモジュールがコンパイルされず excepthook が
# 設定される前に終わるし、`python3` 自体が無い・実行できない場合も同様で、どちらも
# 「stdout 空 ＋ 非0終了」になる。ここで受け止めないと従来どおり無条件 `exit 0` で
# **stdout 空＝allow** に落ち、#340 が塞いだはずの穴が同じ結果のまま残る。
#
# 判定は「stdout が空」だけに依らず **rc と併せて**見る：正常な allow も stdout は空なので、
# 「stdout 空 かつ rc 非0」のときだけ内部エラーとみなす（正常 allow を deny に化けさせない）。
if [ -z "$gate_stdout" ] && [ "$gate_status" -ne 0 ]; then
  printf '%s\n' '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "agent-command-gate: the gate could not run (python3 exited '"$gate_status"' with no decision; e.g. a syntax error in the hook or a missing interpreter). Refusing because the command could not be inspected. This is a bug in the hook, not in the command."}}'
  exit 0
fi

printf '%s' "$gate_stdout"
exit 0
