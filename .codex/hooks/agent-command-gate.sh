#!/usr/bin/env bash
# Codex CLI PreToolUse フックハンドラ（.claude/hooks/agent-command-gate.sh の Codex 版・
# ホワイトリスト方式・Issue #227）。
#
# 役割:
#   "issue-implementer" / "pr-reviewer" subagent（Codex custom subagent の role 名）に対して、
#   push と merge の非対称な権限境界を機械的に強制する。Claude Code 版と同じく、プロンプト指示
#   ではなくハーネス（Codex CLI の PreToolUse フック）で拒否する。
#     - issue-implementer: push・PR作成は可、merge は不可（実装→PR作成までで STOP）。
#     - pr-reviewer:        merge は可、push は不可（レビュー中に無レビューの変更を紛れ込ませられない）。
#   それ以外の agent_type（main／各 *-author 等・agent_type 欠如を含む）はこのゲートの対象外＝許可。
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
# 判定（対象2ロール・シェル系ツールのみ・3層すべてを通過したときだけ許可）:
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
#        `git` / `gh` / `python`・`python3`（**`-m` ＋ unittest|coverage|dsv2|gitgate の形のみ**）で
#        なければ deny。bash/sh/eval/source/xargs/curl/cat/echo/sed/awk/cut/rev/tee… は列挙不要で全 deny。
#   層3: ロール別許可判定（role_command_violation・Issue #227 追加修正3で git ラッパー方式へ転換）
#        gated 2ロールに対し、生 git を一切禁止し gitgate ラッパー verb と gh サブコマンド/フラグだけを許可する。
#        - 先頭 env 代入（`NAME=value`）・`env` ラッパーは deny（`rtk`/`command`/`builtin`/`exec` の純
#          ラッパーのみ剥がして内側を再検査）。
#        - git: 生 `git …` は**全て deny**（raw_git_denied_reason）。git 操作は固定テンプレートの
#          `python3 -m gitgate <verb>` に誘導する（ユーザ制御フラグが git に届かない＝`--receive-pack`/
#          `--upload-pack`/`--output` 等の exec/write 面を構造的に閉じる）。
#        - gitgate: `python3 -m gitgate <verb>` の verb をロール別集合（impl: status/add/commit/push/
#          branch-current/new-branch/fetch/diff/log/publish-info／reviewer: diff/log）で allow/deny する。
#        - gh: `--repo`/`-R` の値スキップのみ先頭で許容・他の先頭 `-*` は deny。サブコマンド
#          （pr/issue は第2トークンも）がロール別集合（impl: pr create / issue view／reviewer: pr
#          view/diff/checks/comment/review/merge/checkout・issue view）に無ければ deny。さらに
#          **per-subcommand フラグ許可リスト**で未知フラグ・`--web`/`--editor` 等の外部起動フラグを deny する。
#        これで再レビュー Critical（`git push --receive-pack=…`・`git log/diff --output=…`）や別名サブ
#        コマンド・config/alias/env 注入による push/merge 迂回（`git send-pack`/`git subtree push`/
#        `git pull`/`git -c alias.x=push`/`gh api …/merge`/`gh alias set` 等）を列挙不要で fail-close 遮断する。
#
# 既知の限界（Issue #129 / #181・多層防御の一枚に過ぎない）:
#   - シェル文字列の静的検査であり sandbox ではない。agent_type の詐称・ハーネス外の実行経路は防げない。
#   - `python3 -m unittest|coverage` はリポジトリ内の Python コードを実行する＝テストファイル経由で
#     任意コードを走らせられる（テスト実行を許可する以上、原理的に閉じられない）。
#   - `git -c <key>=<value>`（alias!/core.pager 等）・`git push --receive-pack=…`・`gh api` 経由の merge・
#     別名サブコマンドでの push は Issue #227 追加修正3（生 git 全 deny＋gitgate ラッパー＋gh フラグ許可
#     リスト）で遮断済み。ただし gitgate も Python 実行を許可する一枚に過ぎず、テストファイル経由の任意
#     コード実行までは閉じられない（原理的限界）。
#   - Codex 側特有: (a) フックは `/hooks` で trust されて初めて発火する、(b) requirements.toml/config.toml で
#     フックが無効化され得る、(c) agent_type に実際どの文字列が入るかは dogfooding で最終確認すべき
#     （AGENT_COMMAND_GATE_DEBUG_PAYLOAD で受信 payload を確認できる）。
#   pr-reviewer.toml / issue-implementer.toml 側のプロンプトレベルの規範と併用する前提。
#
# 入力: PreToolUse フックの stdin JSON（agent_type と tool_name と tool_input.command を想定）。
#   agent_type が issue-implementer/pr-reviewer のいずれでもない場合（欠如を含む）はこのゲートの
#   対象外＝常に許可する。tool_name がシェル系（Bash 等）でない場合も許可する（git/gh は Bash 経由の
#   ため）。シェル系ロールでコマンド文字列が読めない場合は検査不能として deny する（fail-closed）。
#
#   Claude 版と同じオーナー判断を踏襲：agent_type 欠如時（main context 自身）に危険コマンドを
#   fail-closed で deny すると main context の直接 push まで塞ぐ回帰が出るため、「対象外ロールは常に許可」
#   とする（agent_type 詐称防御は失うが、二者択一の上でのオーナー明示判断・Claude issue #129）。
#   Issue #227 でもこの fail-open 設計は**変更しない**（対象は2ロールのみ）。
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
set -u

tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT
cat > "$tmpfile"

python3 - "$tmpfile" <<'PYEOF'
import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone

SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|passwd|authorization|credential|key)", re.I)
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*", re.S)
WRAPPER_COMMANDS = {"rtk", "command", "builtin", "exec"}
GATED_ROLES = {"issue-implementer", "pr-reviewer"}

# 層3（Issue #227 追加修正3・オーナー確定 2026-07-13）: git ラッパー方式＋gh フラグ許可リスト。
# gated 2ロールからは**生 git を一切禁止**し、固定テンプレートで git を呼ぶ薄いラッパー
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
        "new-branch", "fetch", "diff", "log", "publish-info",
    },
    # pr-reviewer: レビューの読取専用のみ（diff/log）。
    "pr-reviewer": {"diff", "log"},
}
GH_SUBCOMMANDS_BY_ROLE = {
    # (subcommand, subsubcommand) の完全一致。pr/issue は第2 bare トークンまで見る。
    "issue-implementer": {("pr", "create"), ("issue", "view")},
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
# Codex がシェルコマンドの hook tool_name として使う canonical 名は "Bash"
# （codex-rs/core/src/tools/hook_names.rs HookToolName::bash()）。git/gh はこの Bash ツール経由で走る。
# 将来 canonical 名が変わっても取りこぼさないよう、代表的なシェル系エイリアスも許容集合に入れる。
# 空文字（tool_name 欠如）は検査不能側に倒して inspect する（fail-closed 寄り）。
SHELL_TOOL_NAMES = {"", "Bash", "shell", "local_shell", "unified_exec", "exec_command"}

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
# 除外（この repo は unittest 方針・AGENTS.md）。coverage は run を禁止し report/html/xml/json のみ許可
# （`coverage run <なんでも>` は任意 Python 実行経路のため）。「-c 禁止したのに coverage run 素通し」の
# 不整合を消し、エージェントの混乱・ハルシネーションリスクを下げる（防御力は #129 限界のため不変）。
ALLOWED_PYTHON_MODULES = {"unittest", "coverage", "dsv2", "gitgate"}
# coverage は実行系サブコマンド（run）を禁止し、レポート出力系のみ許可する。
COVERAGE_ALLOWED_SUBCOMMANDS = {"report", "html", "xml", "json"}


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


# 常時有効の最小トレース（Issue #192）：AGENT_COMMAND_GATE_DEBUG_PAYLOAD（オプトイン・フルペイロード・
# デフォルト無効）とは別に、"フックが実際に呼ばれたか" だけを常時1行追記で残す。command 本文や生 payload
# は含めない（機微情報を持たない設計）。既定パスは AGENT_COMMAND_GATE_TRACE_LOG で上書きでき、空文字を
# 設定すると無効化できる（テストや no-op 運用向け）。既定でオンにしたのは、オプトイン方式だと
# "trust 付与後に本当に発火したか" を確認したいまさにその時に、事前に環境変数を仕込み忘れて再現できない
# という Issue #192 の根本課題を再発させるため（1行判断根拠）。
TRACE_DEFAULT_PATH = os.path.expanduser("~/.codex/agent-command-gate-trace.log")
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


def head_command_violation(tokens):
    """層2: 先頭語ホワイトリスト。許可なら None、違反ならその説明を返す。
    パス付き（`/usr/bin/git`・`./git`）は完全一致しないため deny（カレントディレクトリに `git` という
    名前のスクリプトを置いて実行する迂回を防ぐ＝basename 判定にはしない）。"""
    head = tokens[0]
    if head in ALLOWED_HEAD_COMMANDS:
        return None
    if head in PYTHON_HEAD_COMMANDS:
        modules = "|".join(sorted(ALLOWED_PYTHON_MODULES))
        if len(tokens) >= 3 and tokens[1] == "-m" and tokens[2] in ALLOWED_PYTHON_MODULES:
            # 第2次修正: coverage は run（任意 Python 実行）を禁止し、レポート出力系のみ許可する。
            if tokens[2] == "coverage":
                subcommand = tokens[3] if len(tokens) >= 4 else ""
                if subcommand not in COVERAGE_ALLOWED_SUBCOMMANDS:
                    subs = "|".join(sorted(COVERAGE_ALLOWED_SUBCOMMANDS))
                    return (
                        f"`python3 -m coverage` only allows the report subcommands "
                        f"<{subs}> (`coverage run <...>` executes arbitrary Python and is denied)"
                    )
            return None
        return (
            f"`{head}` is only allowed in the form `{head} -m <{modules}> ...` "
            f"(`-c`, bare scripts and other modules are denied)"
        )
    return (
        f"`{head}` is not in the allowed command whitelist "
        f"(git, gh, python3 -m <{'|'.join(sorted(ALLOWED_PYTHON_MODULES))}>)"
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
            "Write bodies to a file first and pass them via `python3 -m gitgate commit <file>` / "
            "`gh pr create --body-file <file>` / `gh pr comment --body-file <file>`; use native flags "
            "(`gh --jq`, `python3 -m gitgate log --grep <pat> -n <N>`) and the file-reading tools instead of pipes."
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
    head_violation = head_command_violation(tokens)
    if head_violation:
        return (
            f"agent-command-gate ({role}): {head_violation}. "
            "Only git / gh / python3 -m <unittest|coverage|dsv2|gitgate> are allowed for this role "
            "(whitelist mode, Issue #227). Use the file-reading/writing tools for file work."
        )
    violation = role_command_violation(tokens, role)
    if violation:
        return (
            f"agent-command-gate ({role}): {violation}. "
            "Layer 3 (Issue #227) forbids raw git (use `python3 -m gitgate <verb>`) and allows only "
            "this role's gitgate verbs and gh subcommands/flags; config/alias, git/gh global options, "
            "env assignments and cross-role actions (issue-implementer merging, pr-reviewer pushing) are denied."
        )
    return None


reason = None
if agent_type not in GATED_ROLES:
    # 対象外ロール（main context 自身・欠如を含む）は常に許可。上記オーナー判断の通り。
    pass
elif tool_name not in SHELL_TOOL_NAMES:
    # git/gh はシェル(Bash)ツール経由でのみ走る。非シェルツール（apply_patch 等）は対象外。
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
exit 0
