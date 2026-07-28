#!/usr/bin/env bash
# PreToolUse ゲート: agy MCP ツールの workspace を「実在する Windows 絶対パス」に機械的に揃える。
#
# なぜ要るか（2026-07-27 の調査・PR #259）:
#   ブリッジ (/mnt/c/Users/hiras/tools/agy-mcp-bridge/server.py) は workspace を Windows Python の
#   os.path.abspath で正規化する。ドライブレターの無い "/home/..." は「現在ドライブのルート」に
#   解決されるため、MCP サーバの cwd 次第で意味が変わる:
#     - cwd がリポジトリ(UNC)  → \\wsl.localhost\...\<repo>   （偶然正しい）
#     - cwd がドライブ配下      → C:\home\...                  （別物）
#   後者では続く os.makedirs(workspace, exist_ok=True) が**その空ディレクトリを新規作成**し、
#   agy はそこで走る。エラーは出ない。agy はリポジトリを一度も開かないまま自信のある回答を返し、
#   呼び出し側はそれを本物として扱う——これが実際に起きた事故の形。
#   workspace の**省略**も同じ穴（サーバ cwd にフォールバックする）。
#
#   規約（"wslpath -w の絶対パスを明示的に渡す"）は .claude/agents/agy-delegate.md に書いたが、
#   規約は破れる。ここでは破れても正しくなるようにする。
#
# 許可判断は握らない（Codex レビュー指摘2・公式仕様で確認済み）:
#   正規化時は permissionDecision フィールド**自体を出力しない**（= no decision）。このとき
#   updatedInput だけが適用され、許可判断は通常の permission フローにそのまま委ねられる
#   （= フックが無い場合と同じ）。フックが権限境界を広げも狭めもしない。deny だけが例外で、
#   これは意図的なゲート。
#   ※ 明示的な "defer" を返すこととは別物なので、「省略＝defer 相当」とは書かないこと
#     （updatedInput の扱いまで同じだと誤読される・Codex 再レビュー指摘）。
#
# updatedInput は tool_input 全体を返す（Codex レビュー指摘1）:
#   公式スキーマは updatedInput を "partial, merged" と説明するが、全置換と解釈する資料もあり、
#   食い違ったまま prompt 等を失うと事故になる。**元の tool_input を複製して該当フィールドだけ
#   差し替える**形にすれば、merge・置換のどちらの意味でも正しい。安い保険なので常にそうする。
#
# 判定:
#   必須ツールで workspace 未指定        -> deny  … サーバ cwd へ落ちる（意図した repo は推測できない）
#   実在する Windows 絶対パス            -> 素通し … 既に正しい
#   実在する Linux 絶対パス（antigravity）-> 正規化 … wslpath -w で変換（permissionDecision は返さない）
#   実在する Linux 絶対パス（他 backend） -> deny  … パス契約が未検証なので推測変換しない
#   相対パス / 実在しない / 変換失敗      -> deny  … makedirs による無言のディレクトリ生成を手前で止める
#   未知の agy ツール                     -> deny  … tool_input の型に関わらず（分類は名前で先に決める）
#   workspace が期待される所の未知の構造  -> deny  … 検査できないものを通さない
#   解釈できないペイロード / 予期せぬ例外 -> deny  … fail-close
#
# できないこと（規律側の責務・agy-delegate.md 参照）:
#   - 渡されたパスが「意図した repo か」は判定しない（形式と実在の検査のみ）
#   - agy が実際にそれを開いたかは検証できない → アンカー照合は引き続き必須
#   - TOCTOU: 検査から agy 起動までの間の削除・すり替えは防げない
#
# 自動変換の対象外（意図的・過度な一般化を避ける）:
#   codex_* / copilot_* / cursor_*（と agent_swarm の非 antigravity バックエンド）は同じブリッジ経由で
#   **同じ誤解決の穴を持つ**が、それらの CLI が Windows 形式を期待するかは未検証。
#   よって**推測で変換はしない**代わりに、**Windows 絶対パスで来ていなければ deny** して
#   呼び出し側に明示させる。「存在確認だけして値は触らない」ではない（それでは Linux パスが
#   そのままブリッジへ渡り同じ事故が起きる・Codex 再レビュー HIGH）。

set -uo pipefail

# fail-close の外殻（Codex 再レビュー BLOCKER）。
# 非0終了は exit 2 以外ツール実行を止めないため、python が落ちる・見つからない・期限超過しても
# ここで必ず deny JSON に正規化する。これが無いと、検査できなかったときに元の入力のまま実行される。
#
# 期限は「payload 取得＋検査」の全区間に掛ける（Codex 第3巡 BLOCKER）:
#   - stdin が閉じない場合に備え、payload の読み取りにも timeout を掛ける。
#   - timeout には **-k（kill-after）を必ず付ける**。SIGTERM を無視するプロセスは -k 無しでは
#     永久に待たされ、settings.json 側の外殻期限（25秒）に到達してフックごと打ち切られる。
#     そうなると deny を返せない＝未検査の入力がそのまま走る（fail-open）。
#   - SIGKILL 由来の 137 / SIGTERM 由来の 143 も含め、**0 以外はすべて deny へ正規化**する。
#   - python の stdout は**パイプではなくファイル**で受ける。パイプだと孫プロセスが fd を
#     掴んだままだと親が死んでも読み取りが終わらず、期限保証が破れる。
# 最悪ケース = READ_DEADLINE+KILL_AFTER + INNER_DEADLINE+KILL_AFTER = 19 秒 < settings.json の 25 秒。
READ_DEADLINE=5     # stdin から payload を読み切る期限（秒）
INNER_DEADLINE=10   # python 側の総期限（秒）
KILL_AFTER=2        # 終了要求に応答しないプロセスを SIGKILL するまでの猶予（秒）
MAX_BYTES=1048576   # 1MiB を超える payload は読まない（過大入力の歯止め）

emit_deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}\n' "$1"
  exit 0
}

# 作成前に trap を張る（途中で mktemp が失敗しても作れた分は消す）。
payload_file=""; verdict_file=""; stdout_file=""
trap 'rm -f -- "$payload_file" "$verdict_file" "$stdout_file" 2>/dev/null' EXIT
payload_file="$(mktemp 2>/dev/null)" || emit_deny '"agy-workspace-guard: 一時ファイルを作成できず検査不能（fail-close）"'
verdict_file="$(mktemp 2>/dev/null)" || emit_deny '"agy-workspace-guard: 一時ファイルを作成できず検査不能（fail-close）"'
stdout_file="$(mktemp 2>/dev/null)" || emit_deny '"agy-workspace-guard: 一時ファイルを作成できず検査不能（fail-close）"'

timeout -k "$KILL_AFTER" "$READ_DEADLINE" head -c "$MAX_BYTES" >"$payload_file"
read_rc=$?
case "$read_rc" in
  0) ;;
  124|137|143)
    emit_deny '"agy-workspace-guard: ペイロードの読み取りが期限を超過したため拒否（fail-close）"' ;;
  *)
    emit_deny "\"agy-workspace-guard: ペイロードを読めず検査不能 (exit $read_rc)（fail-close）\"" ;;
esac

# 強制終了された子は bash 自身が "Killed ..." を stderr に書き、ヒアドキュメント全文まで
# 吐き出して騒がしいので、その間だけ**自分の** stderr を捨てる。子（python）の stderr は
# fd 3 経由で本物の stderr に出し続ける（診断は失わない）。
exec 3>&2 2>/dev/null
timeout -k "$KILL_AFTER" "$INNER_DEADLINE" python3 - "$payload_file" "$verdict_file" >"$stdout_file" 2>&3 <<'PYEOF'
import json
import os
import re
import subprocess
import sys

# ツールを明示的に分類する。未知のツールは素通しさせない（Codex 再レビュー MEDIUM）。
# 将来 agy に workspace を取るツールが増えたとき、列挙漏れが cwd フォールバックの再発に
# ならないよう、既知の「workspace を取らないツール」だけを allowlist にする。

# workspace(単数・文字列) を必須にするツール。省略するとサーバ cwd へ落ちる。
# codex/copilot/cursor も同じブリッジの Windows Python abspath を通る
# （codex_bridge.py: os.path.abspath(ws) if ws else os.getcwd()）ため同じ穴を持つ。
SINGLE_WS_REQUIRED = {
    "mcp__agy__antigravity_ask",
    "mcp__agy__antigravity_continue",
    "mcp__agy__antigravity_image",
    "mcp__agy__codex_ask",
    "mcp__agy__codex_continue",
    "mcp__agy__copilot_ask",
    "mcp__agy__copilot_continue",
    "mcp__agy__cursor_ask",
    "mcp__agy__cursor_continue",
}
# workspaces(配列) を必須にするツール。省略すると「先頭 workspace かサーバ cwd」へ落ちる。
LIST_WS_REQUIRED = {"mcp__agy__antigravity_image_swarm"}
# tasks[].workspace を必須にするツール。
TASKS_WS_REQUIRED = {"mcp__agy__agent_swarm"}
# workspace を取らない既知ツール（素通しを許す唯一の集合）。
NO_WS_TOOLS = {
    "mcp__agy__antigravity_status",
    "mcp__agy__codex_status",
    "mcp__agy__copilot_status",
    "mcp__agy__cursor_status",
}

# Windows 形式への自動変換を行ってよいバックエンド。antigravity は実測で契約を確認済み
# （--add-dir に UNC を渡して repo を読めることを確認）。他バックエンドはパス契約が未検証
# なので**変換せず、Windows 絶対パスで来ていなければ deny する**（推測で変換しない）。
NORMALIZABLE_BACKENDS = {"antigravity", "agy", "gemini"}

WINDOWS_ABS = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)")
MAX_ITEMS = 64  # 1 呼び出しで検査する workspace の上限（過大入力の歯止め）


class Deny(Exception):
    pass


# 判定 JSON は stdout ではなく **verdict ファイル**へ書く。stdout は「内部処理が最後まで
# 到達した」ことを示す1行のセンチネル専用にする（Codex 第3巡 BLOCKER）。
#   - 初期化メッセージ等が stdout に混ざっても、判定 JSON は汚染されない。
#   - 外殻はセンチネルがちょうど1本あることを要求するので、
#     「rc=0 なのに何も出さなかった」「複数出力した」を素通しにできない。
VERDICT_PATH = sys.argv[2]


def _finish(status, verdict=None):
    if verdict is not None:
        with open(VERDICT_PATH, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(verdict, ensure_ascii=False))
            fh.write("\n")
    sys.stdout.write(f"AGY_GUARD_DONE:{status}\n")
    sys.stdout.flush()
    sys.exit(0)


def emit_pass():
    """検査の結果「何も言うことがない」＝通常フローへ委ねる（明示的な完了表明）。"""
    _finish("pass")


def emit_deny(reason):
    _finish("deny", {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"agy-workspace-guard: {reason}",
        }
    })


def emit_updated_input(tool_input):
    # permissionDecision フィールド自体を出力しない（= no decision）。許可判断は通常フローのまま。
    # 明示的な "defer" を返しているわけではない。
    _finish("updated", {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": tool_input,
        }
    })


def _wslpath(flag, path):
    try:
        proc = subprocess.run(
            ["wslpath", flag, path], capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise Deny(f"wslpath の実行に失敗: {exc}")
    if proc.returncode != 0:
        raise Deny(f"wslpath {flag} が失敗 (exit {proc.returncode}): {proc.stderr.strip()}")
    out = proc.stdout.strip()
    if not out:
        raise Deny(f"wslpath {flag} が空を返した: {path!r}")
    return out


def normalize_workspace(value, label, *, convert):
    """1 つの workspace 値を検査し、正規化後の値を返す。

    convert=False（パス契約が未検証なバックエンド）のときは値を**書き換えない**。
    Windows 絶対パスで来ていれば実在確認だけして通し、そうでなければ deny する
    （「存在確認だけして Linux パスも通す」ではない）。
    """
    if not isinstance(value, str) or not value.strip():
        raise Deny(f"{label} が空、または文字列でない")
    value = value.strip()

    if WINDOWS_ABS.match(value):
        # 既に Windows 形式。存在しない値を通すとブリッジ側 makedirs が空ディレクトリを作るので、
        # WSL 側から見えるパスへ引き戻して実在を確認する。
        linux_view = _wslpath("-u", value)
        if not os.path.isdir(linux_view):
            raise Deny(
                f"{label} のディレクトリが存在しない: {value}"
                f"（WSL から見たパス: {linux_view}）。"
                "存在しない workspace はブリッジ側で新規作成され、agy が空のディレクトリで走る。"
            )
        return value

    if not value.startswith("/"):
        raise Deny(
            f"{label} が相対パス: {value!r}。"
            "解決先が MCP サーバの cwd 依存になるため拒否した。絶対パスを渡すこと。"
        )

    if not os.path.isdir(value):
        raise Deny(f"{label} のディレクトリが存在しない: {value}")

    if not convert:
        # パス契約が未検証なバックエンド。Linux 絶対パスのまま通すと、ブリッジの
        # Windows abspath 解決で C:\home\... 等に化ける（antigravity と同じ事故）。
        # 推測で変換もしないので、ここは deny して呼び出し側に明示させる。
        raise Deny(
            f"{label} が Windows 絶対パスでない: {value}。"
            "このバックエンドのパス契約は未検証のため自動変換しない。"
            "`wslpath -w` で得た Windows 絶対パスを明示的に渡すこと。"
        )

    converted = _wslpath("-w", value)
    if not WINDOWS_ABS.match(converted):
        raise Deny(f"{label} の変換結果が Windows 絶対パスでない: {converted!r}")
    return converted


def handle_single(tool_input, tool_name):
    raw = tool_input.get("workspace")
    if raw is None:
        if tool_name in SINGLE_WS_REQUIRED:
            raise Deny(
                f"{tool_name} に workspace が指定されていない。"
                "省略すると MCP サーバの cwd が使われ、agy が意図しないツリー"
                "（既定プロジェクトの scratch 等）で動いたまま、"
                "エラーを出さずに誤った回答を返す。対象ディレクトリを絶対パスで明示すること"
                "（例: /home/hiras/ws_claude/review-system。Windows 形式へは自動変換する）。"
            )
        return None
    convert = tool_name.startswith("mcp__agy__antigravity_")
    return normalize_workspace(raw, "workspace", convert=convert)


def handle_list(tool_input, tool_name):
    raw = tool_input.get("workspaces")
    if raw is None:
        if tool_name in LIST_WS_REQUIRED:
            raise Deny(
                f"{tool_name} に workspaces が指定されていない。"
                "省略するとサーバ cwd（または先頭 workspace）へ落ちるため拒否した。"
            )
        return None
    if not isinstance(raw, list) or not raw:
        raise Deny(f"workspaces が空、またはリストでない: {type(raw).__name__}")
    if len(raw) > MAX_ITEMS:
        raise Deny(f"workspaces の要素数が上限 {MAX_ITEMS} を超えている: {len(raw)}")
    return [
        normalize_workspace(item, f"workspaces[{idx}]", convert=True)
        for idx, item in enumerate(raw)
    ]


def handle_tasks(tool_input, tool_name):
    raw = tool_input.get("tasks")
    if raw is None:
        if tool_name in TASKS_WS_REQUIRED:
            raise Deny(f"{tool_name} に tasks が無い。検査できないため拒否した。")
        return None
    if not isinstance(raw, list) or not raw:
        raise Deny(f"tasks が空、またはリストでない: {type(raw).__name__}")
    if len(raw) > MAX_ITEMS:
        raise Deny(f"tasks の要素数が上限 {MAX_ITEMS} を超えている: {len(raw)}")

    out = []
    for idx, task in enumerate(raw):
        if not isinstance(task, dict):
            raise Deny(f"tasks[{idx}] がオブジェクトでない: {type(task).__name__}")
        backend = task.get("backend")
        if not isinstance(backend, str) or not backend.strip():
            raise Deny(f"tasks[{idx}].backend が無い。どのバックエンドか判定できないため拒否した。")
        if task.get("workspace") is None:
            raise Deny(
                f"tasks[{idx}] に workspace が指定されていない（backend={backend}）。"
                "省略するとサーバ cwd へ落ち、意図しないツリーで走る。"
            )
        # 値を Windows 形式に変換してよいのは antigravity 系だけ。他バックエンドは
        # パス契約が未検証なので推測変換せず、Windows 絶対パスでなければ deny する。
        convert = backend.strip().lower() in NORMALIZABLE_BACKENDS
        new_task = dict(task)
        new_task["workspace"] = normalize_workspace(
            task["workspace"], f"tasks[{idx}].workspace", convert=convert
        )
        out.append(new_task)
    return out


def main():
    try:
        with open(sys.argv[1], encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        emit_deny(f"PreToolUse ペイロードを解釈できない: {exc}")

    if not isinstance(payload, dict):
        emit_deny(f"PreToolUse ペイロードが object でない: {type(payload).__name__}")

    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.startswith("mcp__agy__"):
        emit_pass()  # agy 以外は素通し

    enforced = SINGLE_WS_REQUIRED | LIST_WS_REQUIRED | TASKS_WS_REQUIRED

    # **ツール名で先に分類する**（Codex 第3巡 MEDIUM）。tool_input の型を先に見ると、
    # 未知ツール＋非 object/欠落 tool_input が「検査対象外」として素通りしてしまう。
    # 分類は allowlist（NO_WS_TOOLS）→ 強制対象（enforced）→ unknown の順で、
    # unknown は tool_input の型に関わらず deny する。
    if tool_name in NO_WS_TOOLS:
        emit_pass()  # workspace を取らないと分かっている既知ツールだけ素通し
    if tool_name not in enforced:
        emit_deny(
            f"{tool_name} は本ゲートの分類表に無い未知の agy ツール。"
            "workspace を取るかどうか判定できないため拒否した（fail-close）。"
            "ツールを追加したら .claude/hooks/agy-workspace-guard.sh の分類表を更新すること。"
        )

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        emit_deny(
            f"{tool_name} の tool_input が object でない"
            f"（{type(tool_input).__name__}）ため検査できず拒否した。"
        )

    updated = dict(tool_input)  # 全フィールドを保持したまま該当キーだけ差し替える
    changed = False

    single = handle_single(tool_input, tool_name)
    if single is not None and single != tool_input.get("workspace"):
        updated["workspace"] = single
        changed = True

    listed = handle_list(tool_input, tool_name)
    if listed is not None and listed != tool_input.get("workspaces"):
        updated["workspaces"] = listed
        changed = True

    tasks = handle_tasks(tool_input, tool_name)
    if tasks is not None and tasks != tool_input.get("tasks"):
        updated["tasks"] = tasks
        changed = True

    if changed:
        emit_updated_input(updated)
    emit_pass()


try:
    main()
except Deny as exc:
    emit_deny(str(exc))
except SystemExit:
    raise
except Exception as exc:  # 予期せぬ例外で素通しさせない（fail-close）
    emit_deny(f"検査中に予期せぬエラー: {type(exc).__name__}: {exc}")
PYEOF
rc=$?
exec 2>&3 3>&-

case "$rc" in
  0) ;;
  # 124=timeout の期限到達 / 137=SIGKILL(-k による強制終了・OOM) / 143=SIGTERM。
  # 終了要求に応答しないプロセスも -k で必ずここへ落ちる。
  124|137|143)
    emit_deny "\"agy-workspace-guard: 検査が内部期限を超過し強制終了された (exit $rc) ため拒否（fail-close）\"" ;;
  *)
    emit_deny "\"agy-workspace-guard: 検査プロセスが異常終了 (exit $rc) のため拒否（fail-close）\"" ;;
esac

# 内部完了の表明を検査する（Codex 第3巡 BLOCKER: stdout 無検証による fail-open）。
# rc=0 でも「何も出さずに終わった」「複数回出した」は検査が成立していない証拠なので deny する。
done_count="$(grep -c '^AGY_GUARD_DONE:' "$stdout_file" 2>/dev/null)" || done_count=0
if [ "$done_count" != "1" ]; then
  emit_deny "\"agy-workspace-guard: 検査の完了表明が 1 本でない (count=$done_count) ため拒否（fail-close）\""
fi
status="$(grep -m 1 '^AGY_GUARD_DONE:' "$stdout_file" | cut -d: -f2)"

case "$status" in
  pass)
    exit 0 ;;  # 検査は成立し「言うことなし」＝通常フローへ委ねる
  deny|updated)
    ;;
  *)
    # $status は JSON へ埋めない（引用符を含む値で判定 JSON 自体が壊れる）。
    emit_deny '"agy-workspace-guard: 検査の完了ステータスが未知のため拒否（fail-close）"' ;;
esac

# 判定 JSON は「単一行の妥当な hookSpecificOutput」以外を通さない。
if [ ! -s "$verdict_file" ]; then
  emit_deny '"agy-workspace-guard: 判定 JSON が生成されなかったため拒否（fail-close）"'
fi
if [ "$(wc -l <"$verdict_file")" -ne 1 ]; then
  emit_deny '"agy-workspace-guard: 判定 JSON が単一行でないため拒否（fail-close）"'
fi
verdict="$(head -n 1 "$verdict_file")"
case "$verdict" in
  '{"hookSpecificOutput":'*'}') ;;
  *) emit_deny '"agy-workspace-guard: 判定 JSON の形式が不正なため拒否（fail-close）"' ;;
esac

printf '%s\n' "$verdict"
exit 0
