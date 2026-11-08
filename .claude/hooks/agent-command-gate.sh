#!/usr/bin/env bash
# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
set -u

project_root="${CLAUDE_PROJECT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)}"

tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT
cat > "$tmpfile"

gate_out="$(mktemp)"
trap 'rm -f "$tmpfile" "$gate_out"' EXIT

set +e
AGENT_COMMAND_GATE_PROJECT_ROOT="$project_root" python3 -I - "$tmpfile" > "$gate_out" <<'PYEOF'
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone

# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
sys.path.insert(0, os.environ["AGENT_COMMAND_GATE_PROJECT_ROOT"])
from agent_command_gate.merge_command import merge_command_reason
from agent_command_gate.graphql_tokens import contains_mutation
from agent_command_gate.launch_origin import launch_origin_reason
from issue_start.gated_roles import GATED_ROLES, READ_ONLY_ROLES, WRITE_ROLES
from codex_worktree_exec.roles import CODEX_EXEC_ROLES

# gh-create-issue gets a narrow Bash command gate without joining GATED_ROLES.
GH_CREATE_ISSUE_ROLE = "gh-create-issue"

SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|passwd|authorization|credential|key)", re.I)
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*", re.S)
WRAPPER_COMMANDS = {"rtk", "command", "builtin", "exec"}

# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
CTX_EXEC_TOOL_SUFFIXES = {"ctx_execute", "ctx_execute_file", "ctx_batch_execute"}

# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
CTX_ALLOWED_LANGUAGES = {"shell"}

# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
GITGATE_VERBS_BY_ROLE = {
    # issue-implementer: 実装→push→PR まで。
    # Phase permission extension adds adopt-branch for the 2b author handover.
    "issue-implementer": {
        "status", "add", "commit", "push", "branch-current",
        "new-branch", "fetch", "diff", "log",
    },
    # The fixer retains its existing PR adoption and base-integration verbs.
    "issue-fixer": {
        "status", "add", "commit", "push", "branch-current",
        "new-branch", "fetch", "diff", "log",
        "adopt-branch", "integrate-base", "integrate-base-continue", "integrate-base-abort",
    },
    # pr-reviewer: レビュー用の読取専用のみ。PR diff は全量を保存する専用verbを使う。
    "pr-reviewer": {"diff", "log", "show-pr-diff"},
}
GH_SUBCOMMANDS_BY_ROLE = {
    # (subcommand, subsubcommand) の完全一致。pr/issue は第2 bare トークンまで見る。
    "issue-implementer": {("pr", "create"), ("pr", "list"), ("pr", "view"), ("issue", "view"), ("api",)},
    "issue-fixer": {("pr", "create"), ("pr", "list"), ("pr", "view"), ("issue", "view"), ("api",)},
    # `gh pr checkout` is excluded because this role shares the primary worktree.
    # Review data is available through `gh pr view`/`diff` and gitgate read verbs.
    "pr-reviewer": {
        ("pr", "list"), ("pr", "view"), ("pr", "diff"), ("pr", "checks"), ("pr", "comment"),
        ("pr", "review"), ("issue", "view"), ("api",),
    },
}
# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
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
    ("pr", "list"): {"value": set(), "bool": set()},
    ("api",): {"value": {"--method", "-X", "--jq", "-q", "-F"}, "bool": {"--paginate", "--slurp"}},
    ("pr", "diff"): {
        "value": {"--color"},
        "bool": {"--no-compact"},
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
    # `("pr", "checkout")` のフラグ集合は **意図的に置かない**（Issue #502 観測2）。
    # `GH_SUBCOMMANDS_BY_ROLE` からも外したので到達しないが、ここに残しておくと
    # 「フラグは定義済み＝許可されている」と誤読され、再付与の敷居が下がる。
}

# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
DANGEROUS_UNQUOTED_CHARS = set("|&;(){}<>$`\n")
# ダブルクォート内で禁止する記号。展開が有効なのは `$`（変数展開・コマンド置換・算術展開）と
# backtick（コマンド置換）だけで、`( ) | ; < > &` はリテラル。よってダブルクォート内の丸括弧は許可する
# （`gh pr create --title "fix(hooks): ..."` の over-deny 防止＝Issue #227 の必須要件）。
DANGEROUS_DOUBLE_QUOTED_CHARS = set("$`")

# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
ALLOWED_HEAD_COMMANDS = {"git", "gh", "pyright"}
PYTHON_HEAD_COMMANDS = {"python", "python3"}
# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
ALLOWED_PYTHON_MODULES = {
    "unittest", "coverage", "dsv2", "gitgate", "asset_parity", "time_fixture_lint",
    "maintainability_lint",
    "feedback_ledger", "issue_envelope",
}
# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
PYTHON_MODULES_BY_ROLE = {
    "issue-fixer": {"karte"},
    "pr-reviewer": {"karte"},
}
# Issue #538 PR-B: Codex に自分の linked worktree で編集とテストだけを行わせるラッパー。
# 付与先と自ロールの起動形は CODEX_EXEC_ROLES と codex_exec_role_violation で検査する。
# 導出・権限境界の理由は docs/methods/codex-workspace-binding.md の D4 を参照。
CODEX_EXEC_MODULE = "codex_worktree_exec"
for _codex_exec_role in sorted(CODEX_EXEC_ROLES):
    PYTHON_MODULES_BY_ROLE.setdefault(_codex_exec_role, set()).add(CODEX_EXEC_MODULE)
# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
KARTE_SUBCOMMANDS_BY_ROLE = {
    "issue-fixer": {"render", "append", "close-attempt", "check", "status"},
    "pr-reviewer": {"ingest-reviewer"},
}
# coverage は実行系サブコマンド（run）を禁止し、レポート出力系のみ許可する。
COVERAGE_ALLOWED_SUBCOMMANDS = {"report", "html", "xml", "json"}
# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
ASSET_PARITY_ALLOWED_SUBCOMMANDS = {"check"}
TIME_FIXTURE_LINT_ALLOWED_SUBCOMMANDS = {"check"}
# Issue #608: baseline の生成は主文脈へ STOP して返し、3ロールには check だけを許可する。
MAINTAINABILITY_LINT_ALLOWED_SUBCOMMANDS = {"check"}
# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
FEEDBACK_LEDGER_SUBCOMMANDS_BY_ROLE = {
    "issue-implementer": {"check", "status", "index"},
    "issue-fixer": {"check", "status", "index"},
    "pr-reviewer": {"check", "status", "index"},
}


from issue_start.phase_role_permissions import extend_phase_permissions
extend_phase_permissions(GITGATE_VERBS_BY_ROLE, GH_SUBCOMMANDS_BY_ROLE,
                         FEEDBACK_LEDGER_SUBCOMMANDS_BY_ROLE)


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


# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
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


# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
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

# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
missing_role_tables = {}
for gated_role in sorted(GATED_ROLES):
    absent = [
        table_name
        for table_name, table in (
            ("GITGATE_VERBS_BY_ROLE", GITGATE_VERBS_BY_ROLE),
            ("GH_SUBCOMMANDS_BY_ROLE", GH_SUBCOMMANDS_BY_ROLE),
            ("FEEDBACK_LEDGER_SUBCOMMANDS_BY_ROLE", FEEDBACK_LEDGER_SUBCOMMANDS_BY_ROLE),
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


def codex_exec_role_violation(tokens, role):
    """Issue #538 D4: `python3 -m codex_worktree_exec` は `--role` がちょうど1つで、その値が
    呼び出し元 agent_type と一致する形だけを通す（implementer が fixer を名乗る等のロール詐称を
    層2 で止める）。ラッパー側は allow_abbrev=False・重複拒否なので `--role`/`--role=` 以外の
    綴りで別の値が効く経路は無い。許可なら None、違反なら理由を返す。"""
    values = []
    index = 3
    while index < len(tokens):
        token = tokens[index]
        if token == "--role":
            values.append(tokens[index + 1] if index + 1 < len(tokens) else "")
            index += 2
            continue
        if token.startswith("--role="):
            values.append(token.split("=", 1)[1])
        index += 1
    if values != [role]:
        return (
            f"`python3 -m {CODEX_EXEC_MODULE}` requires exactly one `--role {role}` "
            f"(the caller's own agent_type); got {values!r}"
        )
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
                karte_verbs = KARTE_SUBCOMMANDS_BY_ROLE.get(role, set())
                if subcommand not in karte_verbs:
                    subs = "|".join(sorted(karte_verbs)) or "(none)"
                    return (
                        f"`python3 -m karte` only allows <{subs}> for this role "
                        "(`ingest-review` writes finding status and belongs to the reviewing side, "
                        "not to the role being reviewed; `decide`/`activate` are main-context only)"
                    )
            if tokens[2] == CODEX_EXEC_MODULE:
                return codex_exec_role_violation(tokens, role)
            if tokens[2] == "issue_envelope":
                if len(tokens) < 4 or tokens[3] not in {"check", "index", "show", "deps", "dependents", "orphans"}:
                    return "`python3 -m issue_envelope` only allows read-only query subcommands"
            if tokens[2] == "maintainability_lint":
                subcommand = tokens[3] if len(tokens) >= 4 else ""
                if subcommand not in MAINTAINABILITY_LINT_ALLOWED_SUBCOMMANDS:
                    subs = "|".join(sorted(MAINTAINABILITY_LINT_ALLOWED_SUBCOMMANDS))
                    return (
                        f"`python3 -m maintainability_lint` only allows <{subs}> "
                        "(baseline generation/update requires STOP and owner confirmation)"
                    )
            # Issue #385: asset_parity / time_fixture_lint はどちらも `check` サブコマンドしか
            # 実装していない read-only 監査ツール。coverage/karte と同型でサブコマンドを固定する。
            if tokens[2] == "asset_parity":
                subcommand = tokens[3] if len(tokens) >= 4 else ""
                if subcommand not in ASSET_PARITY_ALLOWED_SUBCOMMANDS:
                    subs = "|".join(sorted(ASSET_PARITY_ALLOWED_SUBCOMMANDS))
                    return (
                        f"`python3 -m asset_parity` only allows the read-only audit subcommand(s) "
                        f"<{subs}> (it is a presence/absence checker with no write subcommand)"
                    )
            # Issue #522: feedback_ledger は書込み verb を持つため、ロール別の read-only
            # 集合（FEEDBACK_LEDGER_SUBCOMMANDS_BY_ROLE）でしか通さない。
            if tokens[2] == "feedback_ledger":
                allowed_verbs = FEEDBACK_LEDGER_SUBCOMMANDS_BY_ROLE.get(role)
                if allowed_verbs is None:
                    return (
                        "`python3 -m feedback_ledger` is not available to this role "
                        "(the feedback ledger is written by the main context only)"
                    )
                subcommand = tokens[3] if len(tokens) >= 4 else ""
                if subcommand not in allowed_verbs:
                    subs = "|".join(sorted(allowed_verbs))
                    return (
                        f"`python3 -m feedback_ledger` only allows the read-only verbs "
                        f"<{subs}> for this role (recording owner decisions and approving "
                        "proposals belong to the main context, not to a role under review)"
                    )
            if tokens[2] == "time_fixture_lint":
                subcommand = tokens[3] if len(tokens) >= 4 else ""
                if subcommand not in TIME_FIXTURE_LINT_ALLOWED_SUBCOMMANDS:
                    subs = "|".join(sorted(TIME_FIXTURE_LINT_ALLOWED_SUBCOMMANDS))
                    return (
                        f"`python3 -m time_fixture_lint` only allows the read-only audit subcommand(s) "
                        f"<{subs}> (it is a lint checker with no write subcommand)"
                    )
            return None
        return (
            f"`{head}` is only allowed in the form `{head} -m <{modules}> ...` "
            f"(`-c`, bare scripts and other modules are denied)"
        )
    return (
        f"`{head}` is not in the allowed command whitelist "
        f"({', '.join(sorted(ALLOWED_HEAD_COMMANDS))}, python3 -m <{'|'.join(sorted(allowed_modules))}>)"
    )


def raw_git_denied_reason(tokens):
    """Allow bounded repository reads; keep other raw Git operations behind gitgate."""
    index = 1
    while index < len(tokens) and tokens[index] == "-C":
        if index + 1 >= len(tokens):
            return "raw `git -C` is missing its repository path"
        index += 2
    reads = {"status", "log", "diff", "show", "rev-parse"}
    if index < len(tokens) and tokens[index] in reads:
        if any(token in {"-o", "--output", "--ext-diff", "--textconv"} or token.startswith("--output=") for token in tokens[index + 1 :]):
            return "raw Git read options that write files or run external programs are not allowed"
        return None
    return (
        "raw `git` writes and other operations are not allowed for this role; use "
        "`python3 -m gitgate <verb>` instead. Allowed read commands: status, log, diff, show, rev-parse."
    )


def base_integration_reason(command_text, role):
    """PR base 取り込み3verbのロール境界（Issue #706）。

    Issue-pipeline の工程ロール（GATED_ROLES）の中では issue-fixer だけに許可する。
    pipeline 外（主文脈・general-purpose 等）にはこの制約を波及させない。
    GitGate 本体はロールを同定しないため、境界はこの呼び出し元 gate が持つ。
    """
    if role not in GATED_ROLES or role == "issue-fixer":
        return None
    verbs = {"integrate-base", "integrate-base-continue", "integrate-base-abort"}
    for segment in SEGMENT_SPLIT_RE.split(command_text):
        tokens = shell_words(segment) or []
        for index, token in enumerate(tokens):
            if not os.path.basename(token).startswith("python"):
                continue
            cursor = index + 1
            while cursor < len(tokens):
                option = tokens[cursor]
                module_option = re.fullmatch(r"-[^cWXm-]*m(.*)", option)
                if module_option:
                    module = module_option.group(1)
                    if not module:
                        cursor += 1
                        module = tokens[cursor] if cursor < len(tokens) else ""
                    if module in {"gitgate", "gitgate.__main__"} and tokens[cursor + 1:cursor + 2] and tokens[cursor + 1] in verbs:
                        return "PR base integration inside the Issue pipeline is restricted to issue-fixer"
                    break
                value_option = re.fullmatch(r"-[^cWXm-]*[WX](.*)", option)
                if value_option:
                    cursor += 1 if value_option.group(1) else 2
                elif option == "--check-hash-based-pycs":
                    cursor += 2
                elif re.fullmatch(r"-[^cWXm-]+", option):
                    cursor += 1
                else:
                    break
    return None


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


# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
PYRIGHT_FLAG_ALLOWLIST = {
    "value": {"--pythonversion", "--pythonplatform"},
    "bool": {
        "--outputjson", "--stats", "--verbose", "--lib",
        "--skipunannotated", "--ignoreexternal", "--dependencies",
        "-h", "--help", "-V", "--version",
    },
}


def pyright_violation(tokens):
    """層3(pyright・F-510-03): PYRIGHT_FLAG_ALLOWLIST に無いフラグは一律 deny する。
    `--pythonpath`/`--venvpath`/`-v`/`--project`/`-p`/`--typeshedpath`（インタプリタ起動・
    設定ファイル読込）・`--createstub`（書込）・`-w`/`--watch`（対話）はいずれも allowlist に
    無いため、個別の denylist を持たずに一括で deny される。位置引数（型検査対象ファイル）は自由。"""
    value_flags = PYRIGHT_FLAG_ALLOWLIST["value"]
    bool_flags = PYRIGHT_FLAG_ALLOWLIST["bool"]
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break  # 以降はすべて位置引数（型検査対象ファイル）
        if token.startswith("--"):
            name = token.split("=", 1)[0]
            has_eq = "=" in token
            if name in value_flags:
                index += 1 if has_eq else 2
                continue
            if name in bool_flags:
                index += 1
                continue
            return (
                f"`pyright {name}` is not in this role's pyright flag allowlist "
                "(type-checking itself is allowed; interpreter-launching/config-reading "
                "flags such as --pythonpath/--venvpath/--project/--typeshedpath are denied)"
            )
        if token.startswith("-") and len(token) >= 2:
            short = token[:2]
            attached = token[2:]
            if short in value_flags:
                index += 1 if attached else 2
                continue
            if short in bool_flags:
                if attached:
                    return f"`pyright {token}` is not allowed (combined short flags are not permitted)"
                index += 1
                continue
            return (
                f"`pyright {short}` is not in this role's pyright flag allowlist "
                "(type-checking itself is allowed; interpreter-launching/config-reading "
                "flags such as --pythonpath/--venvpath/--project/--typeshedpath are denied)"
            )
        index += 1  # 位置引数（型検査対象ファイル）
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


def gh_has_flag(key, rest, required_flag):
    """rest の option/value 消費を考慮し、required_flag が実際の flag 位置にあるか返す。"""
    value_flags = GH_FLAG_ALLOWLIST.get(key, {"value": set(), "bool": set()})["value"]
    value_flags = value_flags | GH_COMMON_VALUE_FLAGS
    index = 0
    while index < len(rest):
        token = rest[index]
        if token == "--":
            return False
        if token == required_flag:
            return True
        if token.startswith("--"):
            name = token.split("=", 1)[0]
            index += 1 if "=" in token or name not in value_flags else 2
            continue
        if token.startswith("-") and len(token) >= 2:
            short = token[:2]
            index += 1 if token[2:] or short not in value_flags else 2
            continue
        index += 1
    return False


def gh_violation(tokens, role):
    """層3(gh): ロール別の許可サブコマンド＋フラグ判定。許可なら None、違反なら理由文字列を返す。"""
    key, rest = gh_key_and_rest(tokens)
    if key is None:
        return rest  # rest は理由文字列（gh_key_and_rest の global-option 違反）
    if key not in GH_SUBCOMMANDS_BY_ROLE[role]:
        allowed = ", ".join("gh " + " ".join(k) for k in sorted(GH_SUBCOMMANDS_BY_ROLE[role]))
        return f"`gh {' '.join(key).rstrip()}` is not in this role's gh allowlist ({allowed})"
    if key == ("api",):
        for index, token in enumerate(rest):
            if token in {"--method", "-X"} and (index + 1 >= len(rest) or rest[index + 1].upper() not in {"GET", "HEAD"}):
                return "`gh api` allows only GET or HEAD requests for this role"
            if token.startswith("--method=") and token.partition("=")[2].upper() not in {"GET", "HEAD"}:
                return "`gh api` allows only GET or HEAD requests for this role"
            if token.startswith("-X") and len(token) > 2 and token[2:].upper() not in {"GET", "HEAD"}:
                return "`gh api` allows only GET or HEAD requests for this role"
        field_values = [
            (rest[index + 1] if index + 1 < len(rest) else "") if token == "-F"
            else token[2:].lstrip("=")
            for index, token in enumerate(rest) if token == "-F" or token.startswith("-F")
        ]
        if field_values and (
            rest[0] != "graphql" or len(field_values) != 1 or not field_values[0].startswith("query=")
        ):
            return "`gh api -F` is limited to one GraphQL query field for this role"
        if field_values and contains_mutation(field_values[0].partition("=")[2]):
            return "`gh api` GraphQL mutations are not allowed for this role"
        return gh_flag_violation(key, rest)
    if role == "pr-reviewer" and key == ("pr", "diff"):
        if not gh_has_flag(key, rest, "--no-compact"):
            return (
                "Issue #530: pr-reviewer の `gh pr diff` には `--no-compact` が必須です。"
                "rtk の既定圧縮表示は大規模PRでファイル・hunkを丸ごと省略し、レビュー網羅性を損なうためです。"
            )
    return gh_flag_violation(key, rest)



GH_CREATE_ISSUE_ITEM_QUERY = (
    "query($item:ID!){node(id:$item){__typename "
    "... on ProjectV2Item{content{__typename ... on Issue{repository{nameWithOwner}}} "
    "project{id field(name:\"Status\"){__typename "
    "... on ProjectV2SingleSelectField{id name options{id name}}}}}}}"
)


def _option_values(tokens, flag):
    """Return one flag's values, supporting only separate and --flag=value forms."""
    values = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == flag:
            if i + 1 >= len(tokens) or tokens[i + 1].startswith("-"):
                return None
            values.append(tokens[i + 1])
            i += 2
        elif token.startswith(flag + "="):
            values.append(token.partition("=")[2])
            i += 1
        else:
            i += 1
    return values


def _live_project_item(item_id):
    """Read the item content, parent Project and Status in one live snapshot."""
    try:
        result = subprocess.run(
            [
                "gh", "api", "graphql", "-f",
                "query=" + GH_CREATE_ISSUE_ITEM_QUERY,
                "-F", "item=" + item_id,
            ],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode != 0:
            return None
        response = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None
    if not isinstance(response, dict) or response.get("errors"):
        return None
    data = response.get("data")
    node = data.get("node") if isinstance(data, dict) else None
    return node if isinstance(node, dict) and node.get("__typename") == "ProjectV2Item" else None


def _status_option_is_done(project, field_id, option_id):
    """Inspect the same live Project snapshot used for the item scope check."""
    status = project.get("field")
    if (
        not isinstance(status, dict)
        or status.get("__typename") != "ProjectV2SingleSelectField"
        or status.get("name") != "Status"
        or not isinstance(status.get("id"), str)
        or not isinstance(status.get("options"), list)
    ):
        return None
    if status["id"] != field_id:
        return False
    matches = [
        option.get("name") for option in status["options"]
        if isinstance(option, dict) and option.get("id") == option_id
    ]
    if len(matches) != 1:
        return None
    return matches[0] == "Done"


def gh_create_issue_item_edit_violation(rest, target_repository):
    """Bind every field edit to an origin Issue and its live parent Project."""
    item_ids = _option_values(rest, "--id")
    field_ids = _option_values(rest, "--field-id")
    project_ids = _option_values(rest, "--project-id")
    option_ids = _option_values(rest, "--single-select-option-id")
    if any(values is None for values in (item_ids, field_ids, project_ids, option_ids)):
        return "gh project item-edit has a malformed option value"
    if any(len(values) != 1 or not values[0] for values in (item_ids, field_ids, project_ids)):
        return "gh project item-edit requires exactly one non-empty --id, --field-id and --project-id"
    if len(option_ids) > 1:
        return "gh project item-edit accepts only one single-select option"
    node = _live_project_item(item_ids[0])
    content = node.get("content") if node else None
    repository = content.get("repository") if isinstance(content, dict) else None
    project = node.get("project") if node else None
    if (
        not isinstance(content, dict) or content.get("__typename") != "Issue"
        or not isinstance(repository, dict)
        or not isinstance(repository.get("nameWithOwner"), str)
        or repository["nameWithOwner"].casefold() != target_repository
        or not isinstance(project, dict) or project.get("id") != project_ids[0]
    ):
        return "live Project item does not confirm an origin repository Issue in the specified Project"
    if not option_ids:
        return None
    result = _status_option_is_done(project, field_ids[0], option_ids[0])
    if result is None:
        return "live Status metadata is unavailable or inconsistent; item-edit is denied"
    if result:
        return "setting Project Status to Done is denied"
    return None


def gh_create_issue_origin_repository():
    """Resolve the only repository this dispatch may affect from the locked checkout origin."""
    try:
        completed = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=os.getcwd(),
            text=True,
            capture_output=True,
            shell=False,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0 or not isinstance(completed.stdout, str):
        return None
    remote = completed.stdout.rstrip("\n")
    if not remote or "\n" in remote or "\r" in remote:
        return None
    match = re.fullmatch(
        r"(?:https://github\.com/|ssh://git@github\.com/|git@github\.com:)"
        r"([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100}?)(?:\.git)?",
        remote,
    )
    if match is None:
        return None
    return f"{match.group(1)}/{match.group(2)}".casefold()


def gh_create_issue_repo_override_violation(tokens, target_repository):
    """Every gh repo override must match the dispatch's origin-bound target."""
    index = 1
    while index < len(tokens):
        token = tokens[index]
        value = None
        if token in {"--repo", "-R"}:
            if index + 1 >= len(tokens):
                return "gh --repo/-R is missing its repository value"
            value = tokens[index + 1]
            index += 2
        elif token.startswith("--repo="):
            value = token.partition("=")[2]
            index += 1
        elif token.startswith("-R") and len(token) > 2:
            value = token[2:]
            index += 1
        else:
            index += 1
            continue
        if not value or value.casefold() != target_repository:
            return "gh --repo/-R does not match the repository bound at dispatch"
    return None


def gh_create_issue_project_item_add_violation(rest, target_repository):
    """Keep Project item-add scoped to an Issue in the dispatch target repository."""
    urls = []
    index = 0
    while index < len(rest):
        token = rest[index]
        if token == "--url":
            if index + 1 >= len(rest):
                return "project item-add is missing its --url value"
            urls.append(rest[index + 1])
            index += 2
        elif token.startswith("--url="):
            urls.append(token.partition("=")[2])
            index += 1
        else:
            index += 1
    if len(urls) != 1:
        return "project item-add requires exactly one --url"
    match = re.fullmatch(
        r"https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/"
        r"([A-Za-z0-9_.-]{1,100})/issues/[1-9][0-9]*",
        urls[0],
        re.IGNORECASE,
    )
    if match is None or f"{match.group(1)}/{match.group(2)}".casefold() != target_repository:
        return "project item-add URL does not identify an Issue in the repository bound at dispatch"
    return None


def gh_create_issue_api_target_violation(rest, target_repository):
    """Require REST paths to name the same repo as the dispatch target."""
    endpoint = next((token for token in rest if token.startswith("repos/")), "")
    if endpoint:
        path = endpoint.partition("?")[0].partition("#")[0]
        match = re.match(r"repos/([^/]+)/([^/]+)(?:/|$)", path)
        if match is None:
            return "gh api REST endpoint has no verifiable owner/repository"
        repository = f"{match.group(1)}/{match.group(2)}".casefold()
        if repository != target_repository:
            return "gh api REST endpoint does not match the repository bound at dispatch"
        return None
    if rest and rest[0] == "graphql":
        return None
    return "gh api requires a verifiable repository REST endpoint or read-only GraphQL query"


def gh_create_issue_violation(tokens, target_repository):
    """Restrict gh-create-issue commands and bind every GitHub target to the dispatch origin."""
    if not tokens:
        return "empty command"
    override_violation = gh_create_issue_repo_override_violation(tokens, target_repository)
    if override_violation:
        return override_violation
    inherited_repo = os.environ.get("GH_REPO")
    if inherited_repo and inherited_repo.casefold() != target_repository:
        return "GH_REPO does not match the repository bound at dispatch"
    inherited_host = os.environ.get("GH_HOST")
    if inherited_host and inherited_host.casefold() != "github.com":
        return "GH_HOST does not match the GitHub origin bound at dispatch"
    if tokens[0] == "git":
        if tokens in (["git", "branch", "--show-current"], ["git", "remote", "-v"],
                      ["git", "status", "--short"], ["git", "status", "--short", "--branch"]):
            return None
        if len(tokens) == 4 and tokens[:3] == ["git", "remote", "get-url"] and tokens[3] == "origin":
            return None
        return "only bounded read-only git identity commands are permitted"
    if tokens[0] != "gh":
        return "only bounded gh and git read commands are permitted"
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
            return "gh global options other than --repo/-R are denied"
        break
    if index >= len(tokens):
        return "missing gh subcommand"
    command = tokens[index]
    index += 1
    key = (command,)
    if command in {"issue", "label", "project", "repo"} and index < len(tokens):
        key = (command, tokens[index])
        index += 1
    allowed = {
        ("issue", "list"), ("issue", "view"), ("issue", "create"), ("repo", "view"),
        ("label", "list"), ("project", "list"), ("project", "view"),
        ("project", "field-list"), ("project", "item-list"),
        ("project", "item-add"), ("project", "item-edit"), ("api",),
    }
    if key not in allowed:
        return f"gh {' '.join(key)} is outside the gh-create-issue allowlist"
    rest = tokens[index:]
    if key == ("project", "item-add"):
        violation = gh_create_issue_project_item_add_violation(rest, target_repository)
        if violation:
            return violation
    if key == ("project", "item-edit"):
        violation = gh_create_issue_item_edit_violation(rest, target_repository)
        if violation:
            return violation
    if key == ("api",):
        endpoint_violation = gh_create_issue_api_target_violation(rest, target_repository)
        if endpoint_violation:
            return endpoint_violation
        endpoint = next((token for token in rest if token.startswith("repos/")), "")
        field_flags = {"-F", "-f", "--field", "--raw-field"}
        fields = []
        methods = []
        index = 0
        while index < len(rest):
            token = rest[index]
            if token in {"--method", "-X"}:
                if index + 1 >= len(rest):
                    return "gh api method flag is missing its value"
                methods.append(rest[index + 1].upper())
                index += 2
                continue
            if token.startswith("--method="):
                methods.append(token.partition("=")[2].upper())
            elif token.startswith("-X") and len(token) > 2:
                methods.append(token[2:].upper())
            if token in field_flags:
                if index + 1 >= len(rest):
                    return "gh api field flag is missing its value"
                fields.append(rest[index + 1])
                index += 2
                continue
            if token.startswith(("-F", "-f")) and len(token) > 2:
                fields.append(token[2:].lstrip("="))
            elif token.startswith("--field=") or token.startswith("--raw-field="):
                fields.append(token.partition("=")[2])
            index += 1
        if len(set(methods)) > 1:
            return "gh api accepts only one consistent HTTP method for this role"
        method = methods[-1] if methods else ("POST" if fields else "GET")
        if method not in {"GET", "HEAD", "POST"}:
            return "gh api writes are limited to adding issue dependency/sub-issue relations"
        if rest and rest[0] == "graphql":
            query_fields = [value.partition("=")[2] for value in fields if value.startswith("query=")]
            if len(fields) != 1 or len(query_fields) != 1:
                return "gh api GraphQL is limited to one read-only query field for this role"
            if query_fields[0].startswith("@"):
                return "gh api GraphQL query files are not allowed for this role"
            if query_fields and contains_mutation(query_fields[0]):
                return "gh api GraphQL mutations are not allowed for this role"
            allowed_graphql_flags = {"--method", "-X", "--jq", "-q", *field_flags}
            for token in rest[1:]:
                if token.startswith("-") and token not in allowed_graphql_flags \
                        and not token.startswith(("--method=", "-X", "-F", "-f", "--field=", "--raw-field=", "--jq=", "-q")):
                    return "gh api GraphQL accepts only a read-only query and bounded field/output flags"
            return None
        if method in {"GET", "HEAD"}:
            if fields:
                return "gh api fields imply POST and are limited to approved relation writes for this role"
            return gh_flag_violation(key, rest)
        match = re.fullmatch(
            r"repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[1-9][0-9]*/"
            r"(dependencies/blocked_by|sub_issues)",
            endpoint.partition("?")[0].partition("#")[0],
        )
        if method != "POST" or not match:
            return "gh api writes are limited to adding issue dependency/sub-issue relations"
        expected_field = "issue_id" if match.group(1) == "dependencies/blocked_by" else "sub_issue_id"
        for token in rest:
            if token.startswith("-") and token not in {"--method", "-X", *field_flags} \
                    and not token.startswith(("--method=", "-X", "-F", "-f", "--field=", "--raw-field=")):
                return "gh api relation writes accept only method and field options"
        if len(fields) != 1 or not re.fullmatch(expected_field + r"=[1-9][0-9]*", fields[0]):
            return f"gh api relation write requires exactly one numeric {expected_field} field"
        return None
    flags = {
        ("issue", "list"): {"--state", "--search", "--limit", "--json", "--jq", "--assignee", "--label", "--milestone"},
        ("issue", "view"): {"--json", "--jq", "--comments"},
        ("repo", "view"): {"--json", "--jq"},
        ("label", "list"): {"--limit", "--search"},
        ("project", "list"): {"--owner", "--format"},
        ("project", "view"): {"--owner", "--format", "--json", "--jq"},
        ("project", "field-list"): {"--owner", "--format"},
        ("project", "item-list"): {"--owner", "--format", "--query"},
        ("issue", "create"): {"--title", "-t", "--body-file", "-F", "--label", "-l", "--assignee", "-a", "--milestone", "-m"},
        ("project", "item-add"): {"--owner", "--project-number", "--project-id", "--url"},
        ("project", "item-edit"): {"--id", "--project-id", "--field-id", "--text", "--number", "--single-select-option-id", "--date", "--iteration-id"},
    }.get(key, set())
    value_flags = flags | (GH_COMMON_VALUE_FLAGS if key == ("issue", "create") else set())
    index = 0
    while index < len(rest):
        token = rest[index]
        if token.startswith("--"):
            name = token.split("=", 1)[0]
            if name not in value_flags:
                return f"flag {name} is not allowed for gh {' '.join(key)}"
            index += 1 if "=" in token else 2
        elif token.startswith("-"):
            flag = token[:2]
            if flag not in value_flags:
                return f"flag {flag} is not allowed for gh {' '.join(key)}"
            index += 1 if len(token) > 2 else 2
        else:
            index += 1
    return None

def gh_create_issue_gate_reason(command_text):
    symbol = dangerous_shell_symbol(command_text)
    if symbol:
        return f"command contains forbidden shell syntax {symbol}"
    tokens = shell_words(command_text)
    if tokens is None:
        return "command cannot be tokenized"
    tokens, env_reason = strip_wrappers_or_env_reason(tokens)
    if env_reason:
        return f"command wrapper or environment assignment is denied ({env_reason})"
    if not tokens:
        return "command is empty"
    target_repository = gh_create_issue_origin_repository()
    if target_repository is None:
        return "dispatch target repository cannot be resolved from the checkout origin"
    return gh_create_issue_violation(tokens, target_repository)

def role_command_violation(tokens, role):
    """層3: ロール別許可判定。層1・層2 を通過した時点で tokens は「記号を含まない単純な1コマンド」かつ
    先頭語は git/gh/pyright/python -m <module> のいずれか。Git は限定読取と gitgate、gh はサブコマンド
    ＋フラグ許可リスト、pyright は書込系・対話系フラグだけを denylist で拒否
    （Issue #510）、python -m gitgate は verb をロール別集合で判定する。
    その他の python モジュール（unittest 等）は層2 で許可済みでここでは制限しない。"""
    head = tokens[0]
    if head == "git":
        return raw_git_denied_reason(tokens)
    if head == "gh":
        return gh_violation(tokens, role)
    if head == "pyright":
        return pyright_violation(tokens)
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
            "Write bodies to a file (with the Write tool where granted) and pass them via `python3 -m gitgate commit <file>` / "
            "`gh pr create --body-file <file>` / `gh pr comment --body-file <file>`; use native flags "
            "(`gh --jq`, `python3 -m gitgate log --grep <pat> -n <N>`) and this role's Read tool (plus Write/Edit where granted), plus `ctx_search`/`ctx_index` for full-text search, instead of pipes."
        )
    tokens = shell_words(command_text)
    if tokens is None:
        return (
            f"agent-command-gate ({role}): the command cannot be tokenized (unbalanced quotes); "
            "refusing because it cannot be inspected."
        )
    raw_tokens = list(tokens)
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
            f"Only {' / '.join(sorted(ALLOWED_HEAD_COMMANDS))} / python3 -m <{modules}> are allowed "
            "for this role (whitelist mode, Issue #227). Use this role's Read tool (plus Write/Edit where granted) for file work, and `ctx_search`/`ctx_index` for full-text search."
        )
    violation = role_command_violation(tokens, role)
    if violation:
        return (
            f"agent-command-gate ({role}): {violation}. "
            "Layer 3 limits raw git to bounded read commands and allows only "
            "this role's gitgate verbs and gh subcommands/flags; config/alias, git/gh global options, "
            "env assignments and cross-role actions are denied; native settings deny merge for every role."
        )
    if role == "pr-reviewer" and tokens[0] == "gh":
        key, _ = gh_key_and_rest(tokens)
        if key == ("pr", "diff") and (
            not command_text.startswith("rtk ")
            or raw_tokens[:2] != ["rtk", "gh"]
        ):
            return (
                "Issue #530: pr-reviewer の `gh pr diff` は、コマンド文字列の先頭に "
                "リテラル `rtk gh` が必要です。"
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
    merge 検査と `all_role_dangerous_command_token()` / `gate_reason()` を同じ順で適用する。"""
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
    if role in GATED_ROLES or role == GH_CREATE_ISSUE_ROLE:
        cwd = tool_input_obj.get("cwd")
        if cwd is not None:
            return (
                f"agent-command-gate ({role}): an explicit `cwd` is not allowed for this role "
                "(running outside the project root escapes the repo-scoped push/merge boundary). "
                "Omit `cwd` — context-mode pins it to the project root on its own."
            )

    # 1件でも違反があれば呼び出し全体を deny する（部分許可はハーネス側に表現手段がない）。
    for command_text in commands:
        base_reason = base_integration_reason(command_text, role)
        if base_reason:
            return f"agent-command-gate: {base_reason}."
        merge_reason = merge_command_reason(command_text)
        if merge_reason:
            return f"agent-command-gate: {merge_reason}; merge commands are denied for every role."
        token = all_role_dangerous_command_token(command_text)
        if token:
            return (
                f"agent-command-gate: '{token}' is a denied network/exec command for all roles "
                f"(reached via {suffix}; Issue #224/#303)."
            )
        if role == GH_CREATE_ISSUE_ROLE:
            violation = gh_create_issue_gate_reason(command_text)
            if violation:
                return f"agent-command-gate ({role}): {violation}."
        elif role in GATED_ROLES:
            violation = gate_reason(command_text, role)
            if violation:
                return violation
    return None


is_mcp = bool(tool_name) and tool_name.startswith("mcp__")

merge_reason = None
if not is_mcp and isinstance(command, str) and command:
    merge_reason = merge_command_reason(command)

dangerous_token = None
if not is_mcp and isinstance(command, str) and command:
    dangerous_token = all_role_dangerous_command_token(command)

reason = None
base_reason = base_integration_reason(command, agent_type) if isinstance(command, str) else None
if base_reason:
    reason = f"agent-command-gate: {base_reason}."
elif is_mcp:
    # Issue #303: 実行系 MCP 経路。tool_input の形が Bash と違う（`code`+`language` /
    # `commands[]`）ため専用入口で正規化してから、同じ判定関数へ通す。
    reason = ctx_gate_reason(ctx_tool_suffix(tool_name), tool_input, agent_type)
elif merge_reason:
    reason = f"agent-command-gate: {merge_reason}; merge commands are denied for every role."
elif dangerous_token:
    # 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
    reason = (
        f"agent-command-gate: '{dangerous_token}' is a denied network/exec command for all roles "
        "(Issue #224 env-prefix/abspath guard: settings.json permissions.deny is a static prefix match "
        "that env-var prefixes / absolute paths / compound commands can bypass, so this hook denies it "
        "independent of agent_type)."
    )
elif agent_type == "agy-delegate" and not is_mcp:
    symbol = dangerous_shell_symbol(command) if isinstance(command, str) else "missing command"
    tokens = shell_words(command) if isinstance(command, str) and not symbol else None
    tokens, env_reason = strip_wrappers_or_env_reason(tokens) if tokens else ([], None)
    if (symbol or env_reason or len(tokens) < 4 or tokens[0] not in PYTHON_HEAD_COMMANDS
            or tokens[1:3] != ["-m", "agy_delegate"] or tokens[3] not in {"inspect", "run"}):
        reason = "agent-command-gate (agy-delegate): only python3 -m agy_delegate inspect|run is allowed; use Read for file inspection."
    else:
        # 起動元束縛（Codex 版と同一モジュール）: 信頼ルートは hook 位置/CLAUDE_PROJECT_DIR 由来の
        # AGENT_COMMAND_GATE_PROJECT_ROOT。cwd 系が省略されても実プロセス cwd を検査する。
        origin_reason = launch_origin_reason(payload, tool_input, os.environ["AGENT_COMMAND_GATE_PROJECT_ROOT"])
        if origin_reason:
            reason = f"agent-command-gate (agy-delegate): {origin_reason}."
elif agent_type not in GATED_ROLES and agent_type != GH_CREATE_ISSUE_ROLE:
    # 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
    pass
elif not isinstance(command, str) or not command:
    reason = "agent-command-gate: PreToolUse payload does not contain tool_input.command; refusing because the Bash command cannot be inspected."
elif agent_type == GH_CREATE_ISSUE_ROLE:
    reason = gh_create_issue_gate_reason(command)
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

# 設計理由・経緯: .ai/rationale/agent-command-gate-comments.md
if [ -z "$gate_stdout" ] && [ "$gate_status" -ne 0 ]; then
  printf '%s\n' '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "agent-command-gate: the gate could not run (python3 exited '"$gate_status"' with no decision; e.g. a syntax error in the hook or a missing interpreter). Refusing because the command could not be inspected. This is a bug in the hook, not in the command."}}'
  exit 0
fi

printf '%s' "$gate_stdout"
exit 0
