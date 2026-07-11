#!/usr/bin/env bash
# Codex CLI PreToolUse フックハンドラ（.claude/hooks/agent-command-gate.sh の Codex 版）。
#
# 役割:
#   "issue-implementer" / "pr-reviewer" subagent（Codex custom subagent の role 名）に対して、
#   push と merge の非対称な権限境界を機械的に強制する。Claude Code 版と同じく、プロンプト指示
#   ではなくハーネス（Codex CLI の PreToolUse フック）で拒否する。ただしシェル文字列の静的検査
#   には限界があるため、本フックは多層防御の一枚として扱う。
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
# 既知の限界（Issue #129 / #181・多層防御の一枚に過ぎない）:
#   このフックは Bash command 文字列を静的に検査する。直接呼び出し、複数行、環境変数プレフィックス、
#   rtk ラッパー、代表的な bash -c/eval/コマンド置換は検知対象に含めるが、任意のラッパースクリプト、
#   難読化、別インタプリタ内の任意コード、動的に組み立てられるコマンドまでは閉じきれない。
#   加えて Codex 側特有の限界として、(a) フックは `/hooks` で trust されて初めて発火する、
#   (b) requirements.toml/config.toml でフックが無効化され得る、(c) agent_type に実際どの文字列が
#   入るかは dogfooding で最終確認すべき（Claude issue #129 項目1 と同じ fail-open リスク・
#   AGENT_COMMAND_GATE_DEBUG_PAYLOAD で受信 payload を確認できる）。pr-reviewer.toml / issue-implementer.toml
#   側のプロンプトレベルの規範と併用する前提。
#
# 入力: PreToolUse フックの stdin JSON（agent_type と tool_name と tool_input.command を想定）。
#   agent_type が issue-implementer/pr-reviewer のいずれでもない場合（欠如を含む）はこのゲートの
#   対象外＝常に許可する。tool_name がシェル系（Bash 等）でない場合も許可する（git/gh は Bash 経由の
#   ため）。シェル系ロールでコマンド文字列が読めない場合は検査不能として deny する（fail-closed）。
#
#   Claude 版と同じオーナー判断を踏襲：agent_type 欠如時（main context 自身）に危険コマンドを
#   fail-closed で deny すると main context の直接 push まで塞ぐ回帰が出るため、「対象外ロールは常に許可」
#   とする（agent_type 詐称防御は失うが、二者択一の上でのオーナー明示判断・Claude issue #129）。
# デバッグ: AGENT_COMMAND_GATE_DEBUG_PAYLOAD=/path/to/log を設定すると、受信 payload の redacted JSON と
#   判定を追記する（オプトイン・機微値はキー名ベースで伏せる）。
# トレース（Issue #192・常時有効）: 呼ばれるたびに時刻・agent_type・tool_name・判定(allow/deny)のみを
#   既定で ~/.codex/agent-command-gate-trace.log に1行追記する（command 本文・生 payload は含まない）。
#   パスは AGENT_COMMAND_GATE_TRACE_LOG で上書き、空文字で無効化できる。詳細は README.md 参照。
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
SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||[;|\n()]|\$\(|`")
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*", re.S)
WRAPPER_COMMANDS = {"rtk", "command", "builtin", "exec"}
GH_GLOBAL_OPTIONS_WITH_VALUE = {"--repo", "-R", "--hostname"}
GH_GLOBAL_OPTION_VALUE_PREFIXES = ("--repo=", "-R", "--hostname=")
GH_GLOBAL_FLAG_OPTIONS = {"--help", "-h", "--paginate", "--verbose", "--version", "--debug"}
# Codex がシェルコマンドの hook tool_name として使う canonical 名は "Bash"
# （codex-rs/core/src/tools/hook_names.rs HookToolName::bash()）。git/gh はこの Bash ツール経由で走る。
# 将来 canonical 名が変わっても取りこぼさないよう、代表的なシェル系エイリアスも許容集合に入れる。
# 空文字（tool_name 欠如）は検査不能側に倒して inspect する（fail-closed 寄り）。
SHELL_TOOL_NAMES = {"", "Bash", "shell", "local_shell", "unified_exec", "exec_command"}


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


def strip_leading_wrappers(tokens):
    tokens = list(tokens)
    while tokens:
        while tokens and ASSIGNMENT_RE.match(tokens[0]):
            tokens.pop(0)
        if not tokens:
            break
        head = tokens[0]
        if head == "env":
            tokens.pop(0)
            while tokens and (tokens[0].startswith("-") or ASSIGNMENT_RE.match(tokens[0])):
                option = tokens.pop(0)
                if option in {"-u", "-S"} and tokens:
                    tokens.pop(0)
            continue
        if head in WRAPPER_COMMANDS:
            tokens.pop(0)
            continue
        break
    return tokens


def shell_words(segment):
    segment = segment.strip()
    if not segment:
        return []
    try:
        tokens = shlex.split(segment, posix=True)
    except ValueError:
        tokens = segment.split()
    return [token.rstrip(")") for token in tokens if token.rstrip(")")]


def git_subcommand(tokens):
    configs = []
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if token == "-c" and index + 1 < len(tokens):
            configs.append(tokens[index + 1])
            index += 2
            continue
        if token.startswith("-c") and len(token) > 2:
            configs.append(token[2:])
            index += 1
            continue
        if token in {"-C", "--git-dir", "--work-tree", "--namespace"} and index + 1 < len(tokens):
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        break
    subcommand = tokens[index] if index < len(tokens) else ""
    args = tokens[index + 1:] if index < len(tokens) else []
    return subcommand, args, configs


def gh_command(tokens):
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if token in GH_GLOBAL_OPTIONS_WITH_VALUE and index + 1 < len(tokens):
            index += 2
            continue
        if token.startswith(GH_GLOBAL_OPTION_VALUE_PREFIXES) and token not in {"-R"}:
            index += 1
            continue
        if token in GH_GLOBAL_FLAG_OPTIONS:
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        break
    return tokens[index:]


def is_allowed_merge_maintenance(args):
    return len(args) == 1 and args[0] in {"--abort", "--quit"}


def direct_violation(tokens, role):
    tokens = strip_leading_wrappers(tokens)
    if not tokens:
        return None
    if tokens[0] == "git":
        subcommand, args, configs = git_subcommand(tokens)
        if role in {"issue-implementer", "unknown"}:
            if subcommand == "merge" and not is_allowed_merge_maintenance(args):
                return "git merge"
            for config in configs:
                match = re.fullmatch(r"alias\.([A-Za-z0-9_.-]+)=merge", config)
                if match and subcommand == match.group(1):
                    return "git alias for merge"
        if role in {"pr-reviewer", "unknown"} and subcommand == "push":
            return "git push"
    if tokens[0] == "gh" and role in {"issue-implementer", "unknown"}:
        command_tokens = gh_command(tokens)
        if command_tokens[:2] == ["pr", "merge"]:
            return "gh pr merge"
    return None


def quoted_subcommands(command_text):
    patterns = [
        r"\beval\s+(['\"])(.*?)\1",
        r"\b(?:bash|sh|zsh|dash)\s+-c\s+(['\"])(.*?)\1",
        r"\b(?:python3?|perl|ruby|node)\s+-c\s+(['\"])(.*?)\1",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, command_text, re.S):
            yield match.group(2)


def quoted_literals(command_text):
    for match in re.finditer(r"(['\"])(.*?)\1", command_text, re.S):
        yield match.group(2)


def find_violation(command_text, role, depth=0):
    if depth > 3:
        return None
    for segment in SEGMENT_SPLIT_RE.split(command_text):
        violation = direct_violation(shell_words(segment), role)
        if violation:
            return violation
    for nested in quoted_subcommands(command_text):
        violation = find_violation(nested, role, depth + 1)
        if violation:
            return violation
        for literal in quoted_literals(nested):
            violation = find_violation(literal, role, depth + 1)
            if violation:
                return violation
    return None

reason = None
role = agent_type if agent_type in {"issue-implementer", "pr-reviewer"} else "unknown"
if role == "unknown":
    # 対象外ロール（main context 自身・欠如を含む）は常に許可。上記オーナー判断の通り。
    pass
elif tool_name not in SHELL_TOOL_NAMES:
    # git/gh はシェル(Bash)ツール経由でのみ走る。非シェルツール（apply_patch 等）は対象外。
    pass
elif not isinstance(command, str) or not command:
    reason = "agent-command-gate: PreToolUse payload does not contain tool_input.command; refusing because the Bash command cannot be inspected."
else:
    violation = find_violation(command, role)
    if agent_type == "issue-implementer" and violation:
        reason = f"issue-implementer role: {violation} is reserved for pr-reviewer. Push + open a PR, then stop and report."
    elif agent_type == "pr-reviewer" and violation:
        reason = f"pr-reviewer role: {violation} is reserved for issue-implementer. Reviewers may inspect/comment/merge only, never push code."

if reason:
    debug_payload(payload, "deny", reason)
    trace_event(agent_type, tool_name, "deny")
    deny(reason)
else:
    debug_payload(payload, "allow", "")
    trace_event(agent_type, tool_name, "allow")
PYEOF
exit 0
