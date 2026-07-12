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
#
#   2026-07-12 追加是正その3（Issue #213・PR #212 sonnet 再レビューで発見・既存ギャップ）：
#   以下3経路が実際にコマンドを実行するにもかかわらず allow されていた。
#     1. here-string 経由：`bash <<< 'git merge evil'`。HEREDOC_RE は `<<` の直後に識別子を
#        要求するため `<<<`（3文字目が `<`）にはそもそもマッチせず、検知対象外だった。
#     2. xargs プレースホルダ置換経由：`echo 'git merge evil' | xargs -I{} bash -c '{}'`。
#        quoted_subcommands はリテラル文字列 `{}` をそのまま抽出するだけで、実行時に xargs が
#        代入する実際の値（パイプ上流のリテラル）を追えていなかった。
#     3. 一般パイプ経由（ヒアドキュメントを使わない素朴なパイプ）：`printf '%s' 'git merge evil' | bash`。
#   herestring_reexec_bodies/xargs_reexec_bodies/bare_interpreter_reexec_bodies を追加し、
#   いずれも「パイプ上流が echo/printf のみで構成される静的リテラルの場合に限り」実行時に渡る値を
#   静的に確定して reexec 対象に含める設計とした（上流が `find` の結果や変数展開等の非リテラルの
#   場合は静的に決定できないため対象外＝新規の過検知を出さない）。完全な網羅は目指さない（受け入れ
#   基準5）。詳細は各関数のコメント参照（詳細設計は Claude/Codex 両版で同一）。
#
#   2026-07-12 追加是正その4（Issue #215・Issue #213/PR #214 の opus 敵対的レビューで発見）：
#   bare_interpreter_reexec_bodies/xargs_reexec_bodies は literal_producer_value を
#   「直前ステージ（stages[i-1]）のみ」に適用していたため、リテラル producer とインタプリタの
#   間に `cat`/`tee` 等のパススルーを1段挟むと検知が外れていた（`echo 'git merge evil' | cat | bash`
#   等を実行して allow されることを確認済み）。同PR自身のヒアドキュメント経路
#   （heredoc_pipeline_has_downstream_interpreter）は既に多段パススルーに対応済みで、
#   bare-pipe/xargs 経路だけが非対称だった。is_pure_passthrough_stage/
#   literal_producer_value_through_passthrough を追加し、直前ステージが純粋なパススルー
#   （演算子を含まず、cat はファイルオペランドを持たない）である限りさらに前段へ literal
#   producer の確定を遡るよう対称化した。過度なパススルーコマンドの網羅は目指さない（受け入れ
#   基準6・cat/tee の代表例に限定）。詳細は各関数のコメント参照。
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


# here-string 対応（Issue #213 受け入れ基準1）: `<<<`（here-string）は `<<`（ヒアドキュメント）と
# 記法が似ているが意味論が異なる。`<<WORD ... WORD` は終端デリミタまでの複数行を読むのに対し、
# `<<<VALUE` は同じ行の一語（クォート文字列 or 空白なしの単語）をそのままコマンドの標準入力として
# 渡す。HEREDOC_RE は `<<` の直後に識別子（クォート付き/なし）を要求するため、3文字目が `<` である
# `<<<` にはそもそもマッチせず、`bash <<< 'git merge evil'` が検知漏れになっていた（実証済み）。
# 本関数は `<<<` の後続値を抽出し、直前のコマンド語（またはパイプ下流）がインタプリタの場合のみ
# reexec 対象として返す（heredoc_command_word/heredoc_pipeline_has_downstream_interpreter を再利用）。
# ヒアドキュメントと異なり単一行の値であり、除去しなくても direct_violation の素朴な走査に新規の
# 誤検知は生じない（先頭トークンは常にコマンド語であり `<<<` 自体が誤って git/gh と誤認されることは
# ない）ため、scan_text からの除去（ストリップ）は行わない。
HERESTRING_RE = re.compile(r"<<<[ \t]*(?:(['\"])(.*?)\1|(\S+))", re.S)


def herestring_reexec_bodies(command_text):
    bodies = []
    for m in HERESTRING_RE.finditer(command_text):
        value = m.group(2) if m.group(2) is not None else m.group(3)
        if not value:
            continue
        line_end = command_text.find("\n", m.end())
        rest_of_line = command_text[m.end():line_end] if line_end != -1 else command_text[m.end():]
        reaches_interpreter = (
            heredoc_command_word(command_text, m.start()) in HEREDOC_INTERPRETER_COMMANDS
            or heredoc_pipeline_has_downstream_interpreter(rest_of_line)
        )
        if reaches_interpreter:
            bodies.append(value)
    return bodies


# `|`（`||` を除く）でトップレベルのパイプ境界を分割する。SEGMENT_SPLIT_RE 同様、クォート/
# ヒアドキュメント境界を認識しない素朴な分割であり、既存の制約の延長線上にある（安全側＝
# 誤検知が起きても deny 方向にしか倒れない設計であり、完全な網羅は目指さない・受け入れ基準5）。
PIPE_ONLY_RE = re.compile(r"(?<!\|)\|(?!\|)")

# 敵対的自己検証で発見（Issue #213・実装中の追加是正）: `true || echo 'git merge evil' | bash` や
# `echo 'git merge evil' | bash && true` のように、パイプ境界の前後に `&&`/`||`/`;`/改行で
# 別のサブコマンドが連結されていると、ステージ全体をそのまま shlex 解析するだけでは
# producer 側の先頭トークンが `true`（echo ではない）になったり、consumer 側の残余引数に
# `&&`/`true` 等の非フラグ語が混入して「位置引数あり」判定に誤って倒れたりして検知漏れになる。
# シェルの優先順位は `|` が `&&`/`||`/`;` より強く結合するため、producer に実際に効いてくるのは
# その中の最後のサブコマンド、consumer に効いてくるのは最初のサブコマンドのみ。
STAGE_OPERATOR_SPLIT_RE = re.compile(r"&&|\|\||;|\n")


def last_operator_segment(text):
    parts = STAGE_OPERATOR_SPLIT_RE.split(text)
    return parts[-1] if parts else text


def first_operator_segment(text):
    parts = STAGE_OPERATOR_SPLIT_RE.split(text)
    return parts[0] if parts else text


def literal_producer_value(stage_text):
    """パイプの直前ステージのうち実際にパイプへ出力を渡す最後のサブコマンド
    （last_operator_segment）が echo/printf のみで構成され、渡す引数が全てリテラル
    （フラグを含まない単語・クォート文字列）である場合に、標準出力へ書き出される文字列を返す。
    変数展開・コマンド置換・非対応コマンド（`find` 等）が混在する場合は None を返す
    （静的に確定できないため対象外＝新規の過検知を出さない安全側の設計）。"""
    stripped = last_operator_segment(stage_text).strip()
    if "$" in stripped or "`" in stripped:
        return None
    try:
        tokens = shlex.split(stripped, posix=True)
    except ValueError:
        return None
    tokens = strip_leading_wrappers(tokens)
    if len(tokens) < 2:
        return None
    head, args = tokens[0], tokens[1:]
    if any(arg.startswith("-") for arg in args):
        return None
    if head == "echo":
        return " ".join(args)
    if head == "printf":
        if len(args) == 1:
            return args[0]
        if len(args) == 2 and args[0] in {"%s", "%s\\n"}:
            return args[1]
        return None
    return None


# パススルー経由の producer 遡及対応（Issue #215）: bare_interpreter_reexec_bodies/
# xargs_reexec_bodies は下で literal_producer_value を直前ステージ（stages[i-1]）のみに適用して
# いたため、リテラル producer とインタプリタの間に `cat`/`tee` 等のパススルーを1段挟むと
# （`echo 'git merge evil' | cat | bash` 等）検知が外れていた（実行して確認済み）。本節は
# 「直前ステージが純粋なパススルーなら、さらにその前段へ literal_producer_value の確定を
# 遡って試みる」設計で、既存の heredoc_pipeline_has_downstream_interpreter（多段パススルー対応済み）
# と対称化する。過度なパススルーコマンドの網羅は目指さない（受け入れ基準6・代表例の cat/tee に限定）。
PASSTHROUGH_COMMANDS = {"cat", "tee"}


def is_pure_passthrough_stage(stage_text):
    """stage_text（隣接する `|` の間の1ステージ全体のテキスト）が、標準入力をそのまま標準出力へ
    転送するだけの純粋なパススルー（cat/tee）かどうかを判定する。

    安全側に倒す2つの制約:
    1. STAGE_OPERATOR_SPLIT_RE（&&/||/;/改行）を含む場合は対象外にする。シェルの結合優先順位は
       `|` が `&&`/`||`/`;` より強いため、`a | cat && true | b` は実際には
       `(a | cat) && (true | b)` という2本の独立したパイプラインであり、"cat" の出力は
       次段（b）へは渡らない。演算子を含むステージをパススルー候補として遡及すると、実際には
       繋がっていない別のパイプラインを繋がっていると誤認するおそれがあるため、演算子を
       含む時点で遡及を打ち切る（安全側＝新規の過検知にはならず、単に一部の組み合わせを
       検知しないだけに留まる）。
    2. `cat` はファイルオペランド（`-` 以外の非フラグ引数）を持つ場合は対象外にする。
       `echo x | cat somefile | bash` は somefile の中身が実行されるのであって上流の echo の
       値ではないため、パススルー扱いにすると producer 追跡の対応関係が壊れる。`tee` は
       ファイル引数があっても標準入力を標準出力へも常に転送する仕様のため対象外にしない。
    """
    if STAGE_OPERATOR_SPLIT_RE.search(stage_text):
        return False
    stripped = stage_text.strip()
    if "$" in stripped or "`" in stripped:
        return False
    try:
        tokens = shlex.split(stripped, posix=True)
    except ValueError:
        return False
    tokens = strip_leading_wrappers(tokens)
    if not tokens:
        return False
    name = os.path.basename(tokens[0])
    if name not in PASSTHROUGH_COMMANDS:
        return False
    if name == "cat":
        for arg in tokens[1:]:
            if arg == "-" or arg.startswith("-"):
                continue
            return False  # 非フラグのファイルオペランドがある = 標準入力を読まない
    return True


def literal_producer_value_through_passthrough(stages, index):
    """stages[index] から後方（producer 方向）へ、純粋なパススルー段（is_pure_passthrough_stage）を
    許容しながら literal_producer_value が確定できる最初の段まで遡る。パススルーでも literal
    producer でもない段に当たった時点で静的に確定できないため None を返す（安全側）。index は
    毎回1段ずつ減るため、有限のステージ数で必ず終了する（無限ループにはならない）。"""
    while index >= 0:
        value = literal_producer_value(stages[index])
        if value is not None:
            return value
        if not is_pure_passthrough_stage(stages[index]):
            return None
        index -= 1
    return None


# xargs プレースホルダ置換対応（Issue #213 受け入れ基準2）: `echo 'git merge evil' |
# xargs -I{} bash -c '{}'` のように、`-I` で指定したプレースホルダ（既定 `{}`）が xargs 経由で
# 実行時に置換されるパターンは、quoted_subcommands が `bash -c '{}'` を抽出してもプレースホルダの
# リテラル文字列のままで、実際に代入される値（パイプ上流からの入力）を静的に追えず検知漏れに
# なっていた。本関数は、xargs の直前のパイプステージ（またはそこから純粋なパススルー＝cat/tee を
# 許容して遡った先のステージ。Issue #215）が echo/printf のみの静的リテラル引数で構成されている
# 場合に限り（literal_producer_value_through_passthrough が値を確定できる場合のみ）、その値を
# プレースホルダに埋め込んだ上で xargs のコマンド部分を reexec 対象として返す。上流が非リテラル
# の場合は対象外（安全側）。長形式 `--replace` 等の非 `-I` 記法は未対応（既知の残存ギャップ・
# 完全網羅は目指さない設計方針＝受け入れ基準5）。
XARGS_PLACEHOLDER_RE = re.compile(r"(?<!\S)-I[ \t]*(\S+)")


def xargs_reexec_bodies(command_text):
    bodies = []
    stages = PIPE_ONLY_RE.split(command_text)
    for i in range(1, len(stages)):
        stage_text = stages[i]
        try:
            stage_tokens = strip_leading_wrappers(shlex.split(stage_text.strip(), posix=True))
        except ValueError:
            continue
        if not stage_tokens or stage_tokens[0] != "xargs":
            continue
        m = XARGS_PLACEHOLDER_RE.search(stage_text)
        if not m:
            continue
        placeholder = m.group(1)
        remainder = stage_text[m.end():]
        if placeholder not in remainder:
            continue
        literal_value = literal_producer_value_through_passthrough(stages, i - 1)
        if literal_value is None:
            continue
        bodies.append(remainder.replace(placeholder, literal_value))
    return bodies


def bare_interpreter_reexec_bodies(command_text):
    """一般パイプ経由対応（Issue #213 受け入れ基準6）: `printf '%s' 'git merge evil' | bash` の
    ように、ヒアドキュメントを使わない素朴なパイプでインタプリタへ渡す経路を検知する。パイプ
    下流ステージの「最初のサブコマンド」（first_operator_segment。`bash && true` のように後続に
    `&&`/`;` 等で別コマンドが連結されていても、実際にパイプへ繋がるのは最初の一つだけのため）の
    先頭コマンドがインタプリタ（HEREDOC_INTERPRETER_COMMANDS を流用）で、かつ `-c`/`--command`
    や位置引数（スクリプトファイル等）を伴わない（＝標準入力からスクリプト全体を読み込む形）
    場合のみ、上流ステージ（またはそこから純粋なパススルー＝cat/tee を許容して遡った先のステージ。
    Issue #215）の literal_producer_value_through_passthrough を reexec 対象として返す。位置引数が
    ある形（`bash script.sh`／`source FILE` 等）は標準入力をスクリプトとして読まないため対象外とする
    （新規の過検知を避けるため）。"""
    bodies = []
    stages = PIPE_ONLY_RE.split(command_text)
    for i in range(1, len(stages)):
        stage_text = first_operator_segment(stages[i])
        try:
            stage_tokens = strip_leading_wrappers(shlex.split(stage_text.strip(), posix=True))
        except ValueError:
            continue
        if not stage_tokens:
            continue
        name = os.path.basename(stage_tokens[0])
        if name not in HEREDOC_INTERPRETER_COMMANDS:
            continue
        rest_args = stage_tokens[1:]
        if any(arg in {"-c", "--command"} for arg in rest_args):
            continue  # スクリプトが引数そのもの＝quoted_subcommands が別途担当
        if any(not arg.startswith("-") for arg in rest_args):
            continue  # 位置引数（スクリプトファイル等）がある場合は標準入力を読まないため対象外
        literal_value = literal_producer_value_through_passthrough(stages, i - 1)
        if literal_value is None:
            continue
        bodies.append(literal_value)
    return bodies


def find_violation(command_text, role, depth=0):
    if depth > 3:
        return None
    if depth == 0:
        scan_text, reexec_bodies = extract_heredocs(command_text)
    else:
        # depth>0 は quoted_subcommands が eval/bash -c/python -c の引数として抽出した、
        # 既に「再実行される」と判定済みのテキスト。ヒアドキュメント除去はせず素のスキャンを維持する。
        scan_text, reexec_bodies = command_text, []
    # here-string/xargs プレースホルダ/一般パイプ経由の reexec 対象は、ヒアドキュメントと異なり
    # 単一行の判定であるため depth を問わず毎回抽出する（Issue #213）。ただし command_text ではなく
    # scan_text（ヒアドキュメント本文を除去済みのテキスト）を走査対象にする。ヒアドキュメント本文
    # （例: `cat > file.py <<'EOF' ... EOF` で書き出す Python ソース中の文字列リテラル）に
    # 偶然 `<<<`/パイプ/xargs に見える記法が含まれていても、それは実行されないデータであり
    # over-deny してはならない（Issue #189 の false positive 是正方針を踏襲。command_text で
    # 走査すると reaches_interpreter 判定がヒアドキュメント本文内の直前の語だけを見て誤って
    # 「再実行される」と判定してしまう回帰があったため、実装中の敵対的自己検証で発見し是正）。
    reexec_bodies = (
        list(reexec_bodies)
        + herestring_reexec_bodies(scan_text)
        + xargs_reexec_bodies(scan_text)
        + bare_interpreter_reexec_bodies(scan_text)
    )
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
