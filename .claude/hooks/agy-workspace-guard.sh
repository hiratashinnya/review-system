#!/usr/bin/env bash
# PreToolUse ゲート: agy MCP ツールの workspace を「Windows 絶対パス」に機械的に揃える。
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
#
#   規約（"wslpath -w の絶対パスを明示的に渡す"）は .claude/agents/agy-delegate.md に書いたが、
#   規約は破れる。ここでは破れても正しくなるようにする: Linux 絶対パスは wslpath -w で
#   **自動変換して続行**し、変換できないもの・存在しないものだけを拒否する。
#
# 判定:
#   未指定（必須ツールのみ）           -> deny  … 意図した repo は推測できない
#   X:\... / \\...（Windows 形式）      -> allow … 既に正しい
#   Linux 絶対パスで実在するディレクトリ -> allow + updatedInput（wslpath -w で変換）
#   相対パス / 実在しない / 変換失敗     -> deny  … makedirs による無言のディレクトリ生成を手前で止める
#
# できないこと（規律側の責務・agy-delegate.md 参照）:
#   - 渡されたパスが「意図した repo か」は判定しない（形式と実在の検査のみ）
#   - agy が実際にそれを開いたかは検証できない → アンカー照合は引き続き必須
#
# 対象外: codex_* / copilot_* / cursor_* は同じブリッジだが未検証のため強制しない（過剰拒否を避ける）。

set -uo pipefail

payload_file="$(mktemp)"
trap 'rm -f "$payload_file"' EXIT
cat >"$payload_file"

python3 - "$payload_file" <<'PYEOF'
import json
import os
import re
import subprocess
import sys

# workspace を必須にするツール（省略時に cwd 依存で別ツリーへ落ちるもの）。
REQUIRE_WORKSPACE = {
    "mcp__agy__antigravity_ask",
    "mcp__agy__antigravity_continue",
    "mcp__agy__antigravity_image",
}

WINDOWS_ABS = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)")


def emit(decision, reason, updated_input=None):
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    if updated_input is not None:
        out["hookSpecificOutput"]["updatedInput"] = updated_input
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0)


def allow_silently():
    sys.exit(0)


def to_windows_path(path):
    """WSL パス -> Windows 絶対パス。変換できなければ (None, 理由)。"""
    if not os.path.isdir(path):
        return None, f"ディレクトリが存在しない: {path}"
    try:
        proc = subprocess.run(
            ["wslpath", "-w", path],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"wslpath の実行に失敗: {exc}"
    if proc.returncode != 0:
        return None, f"wslpath が失敗 (exit {proc.returncode}): {proc.stderr.strip()}"
    converted = proc.stdout.strip()
    if not converted or not WINDOWS_ABS.match(converted):
        return None, f"wslpath の出力が Windows 絶対パスでない: {converted!r}"
    return converted, None


def normalize_one(value, label):
    """1 つの workspace 値を検査する。戻り値 (正規化後の値 or None, 拒否理由 or None)。"""
    if not isinstance(value, str) or not value.strip():
        return None, f"{label} が空、または文字列でない"
    value = value.strip()
    if WINDOWS_ABS.match(value):
        return value, None  # 既に Windows 形式
    if not value.startswith("/"):
        return None, (
            f"{label} が相対パス: {value!r}。"
            "解決先が MCP サーバの cwd 依存になるため拒否した。絶対パスを渡すこと。"
        )
    converted, err = to_windows_path(value)
    if converted is None:
        return None, f"{label} を Windows パスへ変換できない（{err}）"
    return converted, None


def main():
    try:
        with open(sys.argv[1], encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:  # 検査不能なら fail-close（agent-command-gate と同じ姿勢）
        emit("deny", f"agy-workspace-guard: PreToolUse ペイロードを解釈できない: {exc}")

    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.startswith("mcp__agy__antigravity_"):
        allow_silently()

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        if tool_name in REQUIRE_WORKSPACE:
            emit("deny", f"agy-workspace-guard: {tool_name} の tool_input を検査できないため拒否した。")
        allow_silently()

    has_ws = "workspace" in tool_input and tool_input["workspace"] is not None
    has_wss = "workspaces" in tool_input and tool_input["workspaces"] is not None

    if not has_ws and not has_wss:
        if tool_name in REQUIRE_WORKSPACE:
            emit(
                "deny",
                f"agy-workspace-guard: {tool_name} に workspace が指定されていない。"
                "省略すると MCP サーバの cwd が使われ、agy が意図しないツリー"
                "（既定プロジェクトの scratch 等）で動いたまま、"
                "エラーを出さずに誤った回答を返す。対象ディレクトリを絶対パスで明示すること"
                "（例: /home/hiras/ws_claude/review-system。Windows 形式へは自動変換する）。",
            )
        allow_silently()

    updated = {}
    if has_ws:
        normalized, err = normalize_one(tool_input["workspace"], "workspace")
        if err:
            emit("deny", f"agy-workspace-guard: {err}")
        if normalized != tool_input["workspace"]:
            updated["workspace"] = normalized

    if has_wss:
        raw = tool_input["workspaces"]
        # 既知の形（文字列のリスト）だけ扱う。未知の構造は書き換えず素通しする
        # （過剰拒否を避けるための意図的な穴。agy-delegate.md の規律で補う）。
        if isinstance(raw, list) and raw and all(isinstance(x, str) for x in raw):
            out = []
            changed = False
            for idx, item in enumerate(raw):
                normalized, err = normalize_one(item, f"workspaces[{idx}]")
                if err:
                    emit("deny", f"agy-workspace-guard: {err}")
                changed = changed or normalized != item
                out.append(normalized)
            if changed:
                updated["workspaces"] = out

    if updated:
        detail = "; ".join(f"{k} -> {v}" for k, v in updated.items())
        emit(
            "allow",
            f"agy-workspace-guard: workspace を Windows 絶対パスへ自動変換した（{detail}）。"
            "ブリッジ側の abspath 解決が MCP サーバの cwd に依存し、"
            "無言で別ディレクトリを作ってしまうのを防ぐため。",
            updated_input=updated,
        )

    allow_silently()


main()
PYEOF
