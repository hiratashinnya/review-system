"""agy-workspace-guard.sh（PreToolUse ゲート）の判定テスト。

守っている不変条件（PR #259 の調査で確定）:
  agy ブリッジは workspace を Windows Python の os.path.abspath で解決するため、ドライブレターの
  無い "/home/..." は MCP サーバの cwd 次第で別物になり、続く os.makedirs が**その空ディレクトリを
  無言で新規作成**する。agy はリポジトリを開かないまま自信のある回答を返し、エラーは出ない。
  → workspace は必ず Windows 絶対パスで agy に届くこと（Linux パスは自動変換して救済する）。
"""

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "agy-workspace-guard.sh"
_HAS_BASH = shutil.which("bash") is not None
_HAS_WSLPATH = shutil.which("wslpath") is not None


def run_guard(payload):
    """フックを実行し、返った hookSpecificOutput（無出力＝素通しなら None）を返す。"""
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    result = subprocess.run(
        [str(HOOK)],
        input=raw,
        text=True,
        capture_output=True,
        check=True,
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]


def expect_decision(payload):
    """フックが判定を返すことを要求し、その hookSpecificOutput を返す（素通しなら失敗）。"""
    out = run_guard(payload)
    if out is None:
        raise AssertionError("判定が返るべき入力が素通しした")
    return out


def ask(**tool_input):
    return {"tool_name": "mcp__agy__antigravity_ask", "tool_input": tool_input}


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestScope(unittest.TestCase):
    """検査対象の絞り込み。過剰拒否しないこと。"""

    def test_non_agy_tool_passes_through(self):
        out = run_guard({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        self.assertIsNone(out)

    def test_other_backend_not_enforced(self):
        # codex/copilot/cursor は同じブリッジだが未検証のため対象外（意図的）。
        out = run_guard({"tool_name": "mcp__agy__codex_ask", "tool_input": {"workspace": "/home"}})
        self.assertIsNone(out)

    def test_status_without_workspace_passes_through(self):
        # workspace を取らないツールを必須扱いして塞がないこと。
        out = run_guard({"tool_name": "mcp__agy__antigravity_status", "tool_input": {}})
        self.assertIsNone(out)


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestDeny(unittest.TestCase):
    def _deny_reason(self, payload):
        out = expect_decision(payload)
        self.assertEqual(out["permissionDecision"], "deny")
        return out["permissionDecisionReason"]

    def test_missing_workspace_is_denied(self):
        # 省略＝cwd 依存。これが「別ツリーを見たまま答える」事故の入口だった。
        reason = self._deny_reason(ask(prompt="x"))
        self.assertIn("workspace", reason)

    def test_relative_path_is_denied(self):
        reason = self._deny_reason(ask(workspace="./docs", prompt="x"))
        self.assertIn("相対パス", reason)

    def test_nonexistent_directory_is_denied(self):
        # 実在しないパスを通すと、ブリッジ側 makedirs が空ディレクトリを作ってそこで agy が走る。
        reason = self._deny_reason(ask(workspace="/home/__no_such_dir_for_test__", prompt="x"))
        self.assertIn("存在しない", reason)

    def test_empty_workspace_is_denied(self):
        self._deny_reason(ask(workspace="   ", prompt="x"))

    def test_unparsable_payload_fails_closed(self):
        # 検査できない入力を素通しさせない（agent-command-gate と同じ姿勢）。
        out = expect_decision("not json at all")
        self.assertEqual(out["permissionDecision"], "deny")


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestAllow(unittest.TestCase):
    def test_windows_drive_path_passes_unchanged(self):
        out = run_guard(ask(workspace=r"C:\Users\hiras\proj", prompt="x"))
        self.assertIsNone(out, "既に Windows 形式なら書き換えないこと")

    def test_unc_path_passes_unchanged(self):
        out = run_guard(ask(workspace=r"\\wsl.localhost\Ubuntu\home\hiras", prompt="x"))
        self.assertIsNone(out)

    @unittest.skipUnless(_HAS_WSLPATH, "wslpath が必要（WSL 環境のみ）")
    def test_linux_path_is_converted_in_place(self):
        out = expect_decision(ask(workspace=str(ROOT), prompt="x"))
        self.assertEqual(out["permissionDecision"], "allow")
        converted = out["updatedInput"]["workspace"]
        self.assertTrue(
            converted.startswith("\\\\") or converted[1:3] == ":\\",
            f"Windows 絶対パスでない: {converted!r}",
        )
        # 変換先が元と同じディレクトリを指していること（別ツリーへすり替えていない）。
        self.assertIn(ROOT.name, converted)

    @unittest.skipUnless(_HAS_WSLPATH, "wslpath が必要（WSL 環境のみ）")
    def test_workspaces_list_is_converted_elementwise(self):
        out = expect_decision(
            {
                "tool_name": "mcp__agy__antigravity_swarm",
                "tool_input": {"workspaces": [str(ROOT), os.path.expanduser("~")]},
            }
        )
        self.assertEqual(out["permissionDecision"], "allow")
        converted = out["updatedInput"]["workspaces"]
        self.assertEqual(len(converted), 2)
        for item in converted:
            self.assertTrue(item.startswith("\\\\") or item[1:3] == ":\\")


if __name__ == "__main__":
    unittest.main()
