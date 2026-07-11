#!/usr/bin/env bash
# PreToolUse(Bash) フックハンドラ。
#
# 役割:
#   "issue-implementer" / "pr-reviewer" サブエージェント種別に対して、push と merge の
#   非対称な権限境界を機械的に強制する（プロンプト指示ではなくハーネスで拒否するため、
#   ハーネス側で拒否する。ただしシェル文字列の静的検査には限界があるため、本フックは
#   多層防御の一枚として扱う。
#     - issue-implementer: push・PR作成は可、merge は不可（実装→PR作成までで STOP）。
#     - pr-reviewer:        merge は可、push は不可（レビュー中に無レビューの変更を紛れ込ませられない）。
#   それ以外の agent_type（main／general-purpose／各 *-author 等）はこのゲートの対象外。
#
# 既知の限界（Issue #129・多層防御の一枚に過ぎない）:
#   このフックは Bash command 文字列を静的に検査する。直接呼び出し、複数行、環境変数プレフィックス、
#   rtk ラッパー、代表的な bash -c/eval/コマンド置換は検知対象に含めるが、任意のラッパースクリプト、
#   難読化、別インタプリタ内の任意コード、動的に組み立てられるコマンドまでは閉じきれない。
#   pr-reviewer.md 側のプロンプトレベルの絶対規範（自己承認バイパス禁止）と併用する前提。
#
# 入力: PreToolUse フックの stdin JSON（agent_type/subagent_type と tool_input.command を想定）。
#   command が読めない場合は検査不能として deny する。agent_type が issue-implementer/pr-reviewer の
#   いずれでもない場合（main／general-purpose／各 *-author 等・agent_type 欠如を含む）は、11行目の
#   通りこのゲートの対象外＝常に許可する。
#
#   2026-07-11 是正の経緯：Issue #129 対応で「agent_type 欠如時は危険コマンドを fail-closed で deny」
#   を追加したところ、main context 自身（agent_type を持たない）の git push まで塞ぐ回帰が発生した。
#   オーナー判断：①main context 自身を識別するタグ付けはハーネス側の機能が必要でこのフックだけでは
#   実現不可、②push/merge を専用エージェント以外全面禁止する案は main context の直接 push まで
#   止めるコストが大きく不採用。よって「対象外ロールは常に許可」という元の設計に確定して戻す
#   （fail-closed 化による agent_type 詐称防御は失うが、二者択一の上でのオーナー明示判断）。
# デバッグ: AGENT_COMMAND_GATE_DEBUG_PAYLOAD=/path/to/log を設定すると、受信 payload の redacted JSON と
#   判定を追記する（オプトイン・機微値はキー名ベースで伏せる）。
# トレース（Issue #192・常時有効）: 呼ばれるたびに時刻・agent_type・tool_name・判定(allow/deny)のみを
#   既定で ~/.claude/agent-command-gate-trace.log に1行追記する（command 本文・生 payload は含まない）。
#   パスは AGENT_COMMAND_GATE_TRACE_LOG で上書き、空文字で無効化できる。詳細は .codex/hooks/README.md 参照
#   （Codex 版と同じ設計。Claude 版の README には現状フック一覧の記載がないため参照先を明記）。
#
#   2026-07-11 是正の経緯（Issue #189）：quoted_subcommands/quoted_literals による難読化対策の
#   副作用で、`gh pr create --body "$(cat <<'EOF' ... EOF)"` のようにヒアドキュメントで PR 本文・
#   コミットメッセージを渡す（本フック自身の運用規約が推奨する書き方）際、本文中の散文的な引用
#   （例: Markdown インラインコード `git merge`）を独立したトップレベルコマンドと誤認して
#   over-deny していた。ヒアドキュメント本文はシェル上「直前コマンドへの入力データ」であって
#   コマンド列ではないため、direct_violation の素朴な走査対象から除外し、実際にインタプリタへの
#   入力として再実行される場合（`bash <<'EOF' ... EOF` 等）だけ本文を素のテキストとして再帰走査する
#   よう是正した（詳細は find_violation/extract_heredocs のコメント参照）。既存の eval/bash -c/
#   python -c 経由の難読化検知（quoted_subcommands）は無変更。
#
#   2026-07-12 追加是正（Issue #189・pr-reviewer レビュー指摘・PR #212）：上記の是正が
#   heredoc_command_word() で「`<<` の直前・同一行のコマンド語」しか見ておらず、その stdout が
#   下流パイプでインタプリタに渡る経路（`cat <<'EOF' | bash` / `cat <<EOF | bash`（非引用デリミタ）/
#   `cat <<-'EOF' | bash`（`<<-` ダッシュ版）/ `cat <<'EOF' | tee /tmp/x | bash`（多段パイプ）等）を
#   捕捉できておらず、本来 deny すべきものが軒並み allow される重大バイパスがあった。
#   「本文を除外する前に、そのヒアドキュメントが最終的にインタプリタへ渡る経路（直接 `bash <<EOF`
#   でも、パイプ経由でも）が無いことを確認できた場合のみ除外する」という、より保守的な（除外条件を
#   厳しくする）方向で heredoc_pipeline_has_downstream_interpreter() を追加し、マーカー行内の
#   パイプ下流ステージにインタプリタが見つかれば reexec_bodies に含めて depth+1 で再帰走査するよう
#   拡張した（詳細は heredoc_pipeline_has_downstream_interpreter/extract_heredocs のコメント参照）。
#
#   2026-07-12 追加是正その2（Issue #189・PR #212 再レビュー指摘）：HEREDOC_INTERPRETER_COMMANDS に
#   bash 組み込みの `source`/`.`（同義・カレントシェルでスクリプトを再実行するコマンド）が含まれて
#   おらず、`cat <<'EOF' | source /dev/stdin`（`. /dev/stdin` も同様）でヒアドキュメント本文が
#   再実行されるにもかかわらず allow されていた（PR #212 の base=main では偶然 deny されていた挙動が
#   本PRの変更で allow に変わる回帰だった）。source/. を HEREDOC_INTERPRETER_COMMANDS に追加して是正。
# 標準ライブラリのみで JSON をパースする（jq 非依存・CLAUDE.md の "python3 標準ライブラリのみ" 方針に合わせる）。
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
# tool_name は判定ロジックには使わない（Claude 側は settings.json の matcher:"Bash" で既に絞り込み済み）。
# トレースログの診断用にのみ拾う。
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


# ヒアドキュメント対応（Issue #189）: ヒアドキュメント本文（<<WORD / <<'WORD' / <<"WORD" ... WORD）は
# シェル上「直前のコマンドへの入力データ」であり、トップレベルのコマンド列ではない。しかし
# SEGMENT_SPLIT_RE ベースの素朴な分割は改行・丸括弧・バッククォートを無条件にコマンド境界とみなすため、
# ヒアドキュメント経由で渡す PR 本文・コミットメッセージの散文（Markdown のインラインコード
# `git merge` 等）を独立したトップレベルコマンドと誤認し、over-deny していた（Issue #189 で
# `gh pr create --body "$(cat <<'EOF' ... EOF)"` 等が実地で複数回誤検知された）。
# 対策: ヒアドキュメント本文を direct_violation のトップレベル走査から除外する。ただし
# `bash <<'EOF' ... EOF` のように本文が実際にインタプリタへのスクリプト入力として再実行される
# 場合は、除外した上で別途 depth+1 として本文の素のテキストを再帰走査し、既存の false negative
# 対策と同じ安全側バイアスを維持する。
# 適用は depth==0（エージェントが実際に発行したコマンド全体）のみに限定する。depth>0
# （quoted_subcommands が eval/bash -c/python -c の引数として抽出した文字列）は、その時点で
# 既に「再実行される」と判定済みのテキストなので、ヒアドキュメント除去はせず素の最大感度スキャンを
# 維持する（`bash -c "$(cat <<'EOF'\ngit merge evil\nEOF\n)"` のような二重の難読化を見逃さないため）。
HEREDOC_RE = re.compile(
    r"<<-?[ \t]*(?:'([A-Za-z_][A-Za-z0-9_]*)'|\"([A-Za-z_][A-Za-z0-9_]*)\"|([A-Za-z_][A-Za-z0-9_]*))"
)
# quoted_subcommands() が "-c" 経由の再実行として扱っているコマンド集合と揃える
# （bash/sh/zsh/dash と python3?/perl/ruby/node）。ヒアドキュメントを直接標準入力として
# 食わせるコマンド（`bash <<EOF` 等）も同じ意味で「本文が実行される」ため同じ集合を使う。
# `source`/`.`（bash 組み込みの同義コマンド。カレントシェルでスクリプトを読み込み実行する）も
# 同様に本文が実行されるため含める（2026-07-12 追加是正・Issue #189・PR #212 再レビュー指摘）。
HEREDOC_INTERPRETER_COMMANDS = {
    "bash", "sh", "zsh", "dash", "python", "python3", "perl", "ruby", "node", "source", ".",
}


def heredoc_command_word(command_text, marker_start):
    """`<<` の直前（同じ行内）にあるコマンド語を返す（先頭が '-' のフラグ語はスキップする）。
    見つからなければ空文字列を返す（= 非インタプリタ扱い・安全側でスキップのみに倒す）。"""
    line_start = command_text.rfind("\n", 0, marker_start) + 1
    prefix = command_text[line_start:marker_start]
    words = prefix.split()
    for word in reversed(words):
        if word.startswith("-"):
            continue
        return os.path.basename(word.rstrip("|;&"))
    return ""


def heredoc_pipeline_has_downstream_interpreter(line_after_marker):
    """ヒアドキュメントのマーカー以降・同じ行の末尾までのテキストを走査し、パイプ（`|`）で
    区切られた下流ステージの先頭コマンドがインタプリタかどうかを判定する（Issue #189 追加是正・
    PR #212 レビュー指摘）。

    是正の経緯: heredoc_command_word() は `<<` の直前・同一行のコマンド語（例: `cat`）しか
    見ておらず、その stdout がパイプ下流のインタプリタへ渡る経路（`cat <<'EOF' | bash` /
    `cat <<EOF | bash`（非引用デリミタ）/ `cat <<-'EOF' | bash`（`<<-` ダッシュ版）/
    `cat <<'EOF' | tee /tmp/x | bash`（多段パイプ）等）を捕捉できておらず、本来 deny すべきものが
    軒並み allow される重大バイパスがあった。
    設計方針: 「本文を除外する前に、そのヒアドキュメントが最終的にインタプリタへ渡る経路
    （直接 `bash <<EOF` でも、パイプ経由でも）が無いことを確認できた場合のみ除外する」という、
    より保守的な（除外条件を厳しくする）方向に倒す。マーカー行内の各パイプステージについて
    strip_leading_wrappers で env/rtk 等のラッパーとフラグ・代入を剥がした先頭コマンド語を見て、
    どこかにインタプリタがあれば「最終的に再実行される」と判定する。"""
    for stage in line_after_marker.split("|")[1:]:
        tokens = strip_leading_wrappers(stage.split())
        if not tokens:
            continue
        name = os.path.basename(tokens[0].rstrip("|;&"))
        if name in HEREDOC_INTERPRETER_COMMANDS:
            return True
    return False


def extract_heredocs(command_text):
    """ヒアドキュメント本文をトップレベル走査用テキストから取り除き、
    (取り除いた後のテキスト, インタプリタへ直接渡される本文のリスト) を返す。
    本文は常に direct_violation の素朴な分割対象から除外する一方、本文がインタプリタコマンドへの
    標準入力として渡される場合（`bash <<'EOF' ... EOF` の直接形、または `cat <<'EOF' | bash` の
    ようにパイプ下流でインタプリタに渡る形のいずれか。Issue #189 追加是正）は、その本文を
    呼び出し側（find_violation）で depth+1 として再帰走査させる。終端デリミタが見つからない
    不正な形式のヒアドキュメントはテキストを変更せず残す（検査不能側＝安全側に倒す）。"""
    stripped = []
    reexec_bodies = []
    pos = 0
    for m in HEREDOC_RE.finditer(command_text):
        if m.start() < pos:
            continue  # 既に取り除いた本文の内側にある偽陽性マッチ
        word = m.group(1) or m.group(2) or m.group(3)
        line_end = command_text.find("\n", m.end())
        if line_end == -1:
            continue  # 本文を持たない（改行がない）= 不正形式、そのまま残す
        body_start = line_end + 1
        delim_re = re.compile(r"(?m)^[ \t]*" + re.escape(word) + r"[ \t]*$")
        dm = delim_re.search(command_text, body_start)
        if not dm:
            continue  # 終端デリミタが見つからない = 不正形式、そのまま残す
        stripped.append(command_text[pos:body_start])
        reaches_interpreter = (
            heredoc_command_word(command_text, m.start()) in HEREDOC_INTERPRETER_COMMANDS
            or heredoc_pipeline_has_downstream_interpreter(command_text[m.end():line_end])
        )
        if reaches_interpreter:
            reexec_bodies.append(command_text[body_start:dm.start()])
        pos = dm.start()
    stripped.append(command_text[pos:])
    return "".join(stripped), reexec_bodies


def find_violation(command_text, role, depth=0):
    if depth > 3:
        return None
    if depth == 0:
        scan_text, reexec_bodies = extract_heredocs(command_text)
    else:
        # depth>0 は quoted_subcommands が eval/bash -c/python -c の引数として抽出した、
        # 既に「再実行される」と判定済みのテキスト。ヒアドキュメント除去はせず素のスキャンを維持する。
        scan_text, reexec_bodies = command_text, []
    for segment in SEGMENT_SPLIT_RE.split(scan_text):
        violation = direct_violation(shell_words(segment), role)
        if violation:
            return violation
    for body in reexec_bodies:
        violation = find_violation(body, role, depth + 1)
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
if not isinstance(command, str) or not command:
    reason = "agent-command-gate: PreToolUse payload does not contain tool_input.command; refusing because the Bash command cannot be inspected."
else:
    role = agent_type if agent_type in {"issue-implementer", "pr-reviewer"} else "unknown"
    violation = find_violation(command, role)
    if agent_type == "issue-implementer" and violation:
        reason = f"issue-implementer role: {violation} is reserved for pr-reviewer. Push + open a PR, then stop and report."
    elif agent_type == "pr-reviewer" and violation:
        reason = f"pr-reviewer role: {violation} is reserved for issue-implementer. Reviewers may inspect/comment/merge only, never push code."
    # agent_type が上記2ロール以外（欠如を含む）の場合は対象外＝常に許可（11行目のドキュメント通り）。

if reason:
    debug_payload(payload, "deny", reason)
    trace_event(agent_type, tool_name, "deny")
    deny(reason)
else:
    debug_payload(payload, "allow", "")
    trace_event(agent_type, tool_name, "allow")
PYEOF
exit 0
