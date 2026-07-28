"""agy-workspace-guard.sh（PreToolUse ゲート）の判定テスト。

守っている不変条件（PR #259 の調査で確定）:
  agy ブリッジは workspace を Windows Python の os.path.abspath で解決するため、ドライブレターの
  無い "/home/..." は MCP サーバの cwd 次第で別物になり、続く os.makedirs が**その空ディレクトリを
  無言で新規作成**する。agy はリポジトリを開かないまま自信のある回答を返し、エラーは出ない。
  → workspace は必ず「実在する Windows 絶対パス」で agy に届くこと（Linux パスは自動変換で救済）。

Codex レビュー（#259）で塞いだ穴もここで固定する:
  - updatedInput が tool_input 全体を保持すること（prompt 等の欠落＝BLOCKER）
  - 正規化時に permissionDecision を返さないこと（許可判断を握らない＝"defer" 相当）
  - agent_swarm / image_swarm が matcher と必須判定から漏れないこと
  - 実在しない Windows パス・未知構造・非 object ペイロードで fail-open しないこと
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "agy-workspace-guard.sh"
_HAS_BASH = shutil.which("bash") is not None

# wslpath は WSL にしか無いが、主要な回帰（入力全保持・権限判断不返却・変換の往復・
# 未知ツール deny）を WSL 以外の CI で skip すると守れない。実物が無ければ **同じ規則の
# 代替を PATH に差し込んで**全環境で回す（Codex 再レビュー MEDIUM: 環境依存 skip）。
_FAKE_WSLPATH = r"""#!/usr/bin/env python3
import sys
flag, path = sys.argv[1], sys.argv[2]
if flag == "-w":
    if path.startswith("/mnt/") and len(path) > 6:
        d = path[5]; sys.stdout.write(d.upper() + ":\\" + path[7:].replace("/", "\\"))
    else:
        sys.stdout.write("\\\\wsl.localhost\\Ubuntu" + path.replace("/", "\\"))
else:
    p = path.replace("\\", "/")
    if p.startswith("//wsl.localhost/Ubuntu"):
        sys.stdout.write(p[len("//wsl.localhost/Ubuntu"):] or "/")
    elif len(p) > 1 and p[1] == ":":
        sys.stdout.write("/mnt/" + p[0].lower() + p[2:])
    else:
        sys.stdout.write(p)
sys.stdout.write("\n")
"""

_shim_dir = None


def setUpModule():
    """wslpath が無い環境では代替を用意し、PATH の先頭に差す。"""
    global _shim_dir
    if shutil.which("wslpath"):
        return
    _shim_dir = tempfile.mkdtemp(prefix="wslpath_shim_")
    shim = Path(_shim_dir) / "wslpath"
    shim.write_text(_FAKE_WSLPATH, encoding="utf-8")
    shim.chmod(0o755)
    os.environ["PATH"] = f"{_shim_dir}{os.pathsep}{os.environ['PATH']}"


def tearDownModule():
    if _shim_dir:
        shutil.rmtree(_shim_dir, ignore_errors=True)


def run_guard(payload):
    """フックを実行し、返った hookSpecificOutput（無出力＝素通しなら None）を返す。"""
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    result = subprocess.run(
        [str(HOOK)], input=raw, text=True, capture_output=True, check=True
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]


def expect_decision(payload):
    """フックが何か返すことを要求し、その hookSpecificOutput を返す（素通しなら失敗）。"""
    out = run_guard(payload)
    if out is None:
        raise AssertionError("判定が返るべき入力が素通しした")
    return out


def ask(**tool_input):
    return {"tool_name": "mcp__agy__antigravity_ask", "tool_input": tool_input}


def swarm(*tasks):
    return {"tool_name": "mcp__agy__agent_swarm", "tool_input": {"tasks": list(tasks)}}


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestScope(unittest.TestCase):
    """検査対象の絞り込み。過剰拒否しないこと。"""

    def test_non_mcp_tool_passes_through(self):
        self.assertIsNone(run_guard({"tool_name": "Bash", "tool_input": {"command": "ls"}}))

    def test_other_backend_tool_without_workspace_passes_through(self):
        # codex/copilot/cursor は同じブリッジだが Windows 形式を期待するか未検証＝対象外（意図的）。
        self.assertIsNone(
            run_guard({"tool_name": "mcp__agy__codex_status", "tool_input": {}})
        )

    def test_status_without_workspace_passes_through(self):
        # workspace を取らないツールを必須扱いして塞がないこと。
        self.assertIsNone(
            run_guard({"tool_name": "mcp__agy__antigravity_status", "tool_input": {}})
        )


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestDeny(unittest.TestCase):
    def _deny_reason(self, payload):
        out = expect_decision(payload)
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertNotIn("updatedInput", out, "deny 時に入力を書き換えないこと")
        return out["permissionDecisionReason"]

    def test_missing_workspace_is_denied(self):
        # 省略＝cwd 依存。これが「別ツリーを見たまま答える」事故の入口だった。
        self.assertIn("workspace", self._deny_reason(ask(prompt="x")))

    def test_relative_path_is_denied(self):
        self.assertIn("相対パス", self._deny_reason(ask(workspace="./docs", prompt="x")))

    def test_nonexistent_linux_directory_is_denied(self):
        self.assertIn(
            "存在しない",
            self._deny_reason(ask(workspace="/home/__no_such_dir_for_test__", prompt="x")),
        )

    def test_nonexistent_windows_directory_is_denied(self):
        # 旧版は Windows 形式なら無検証で通していた。`C:\home\...` はブリッジ側 makedirs が
        # 作ってしまう典型なので、ここで止める。
        self.assertIn(
            "存在しない",
            self._deny_reason(ask(workspace=r"C:\home\hiras\__bogus__", prompt="x")),
        )

    def test_empty_workspace_is_denied(self):
        self._deny_reason(ask(workspace="   ", prompt="x"))

    def test_unparsable_payload_fails_closed(self):
        self._deny_reason("not json at all")

    def test_non_object_payload_fails_closed(self):
        self.assertIn("object でない", self._deny_reason([1, 2, 3]))

    def test_swarm_task_without_workspace_is_denied(self):
        # matcher が antigravity_ 前方一致だった頃はここが素通りしていた（Codex 指摘のバイパス）。
        self.assertIn(
            "workspace",
            self._deny_reason(swarm({"backend": "antigravity", "prompt": "x"})),
        )

    def test_swarm_task_without_backend_is_denied(self):
        self.assertIn(
            "backend",
            self._deny_reason(swarm({"prompt": "x", "workspace": str(ROOT)})),
        )

    def test_swarm_unknown_task_structure_is_denied(self):
        # 未知構造を素通しにすると検査を回避できてしまう（fail-open を塞ぐ）。
        self._deny_reason(swarm("not-an-object"))

    def test_image_swarm_without_workspaces_is_denied(self):
        self.assertIn(
            "workspaces",
            self._deny_reason(
                {
                    "tool_name": "mcp__agy__antigravity_image_swarm",
                    "tool_input": {"prompts": ["a"]},
                }
            ),
        )

    def test_empty_workspaces_list_is_denied(self):
        self._deny_reason(
            {
                "tool_name": "mcp__agy__antigravity_image_swarm",
                "tool_input": {"prompts": ["a"], "workspaces": []},
            }
        )

    def test_too_many_items_is_denied(self):
        self.assertIn(
            "上限",
            self._deny_reason(
                {
                    "tool_name": "mcp__agy__antigravity_image_swarm",
                    "tool_input": {"prompts": ["a"], "workspaces": [str(ROOT)] * 65},
                }
            ),
        )


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestAllow(unittest.TestCase):
    def test_existing_windows_path_passes_unchanged(self):
        win = subprocess.run(
            ["wslpath", "-w", str(ROOT)], capture_output=True, text=True, check=True
        ).stdout.strip()
        self.assertIsNone(
            run_guard(ask(workspace=win, prompt="x")), "既に正しい値は書き換えないこと"
        )

    def test_linux_path_is_converted(self):
        out = expect_decision(ask(workspace=str(ROOT), prompt="x"))
        converted = out["updatedInput"]["workspace"]
        self.assertTrue(
            converted.startswith("\\\\") or converted[1:3] == ":\\",
            f"Windows 絶対パスでない: {converted!r}",
        )
        # 変換先が元と同じディレクトリを指していること（別ツリーへすり替えていない）。
        back = subprocess.run(
            ["wslpath", "-u", converted], capture_output=True, text=True, check=True
        ).stdout.strip()
        self.assertEqual(os.path.realpath(back), os.path.realpath(str(ROOT)))

    def test_updated_input_preserves_all_other_fields(self):
        """BLOCKER 回帰: updatedInput が workspace だけだと prompt が失われうる。"""
        out = expect_decision(
            ask(workspace=str(ROOT), prompt="KEEP_ME", timeout_s=180, watch=False)
        )
        updated = out["updatedInput"]
        self.assertEqual(updated["prompt"], "KEEP_ME")
        self.assertEqual(updated["timeout_s"], 180)
        self.assertIs(updated["watch"], False)

    def test_normalization_does_not_decide_permission(self):
        """正規化はフックの仕事だが、許可判断は通常フローに委ねる（"defer" 相当）。"""
        out = expect_decision(ask(workspace=str(ROOT), prompt="x"))
        self.assertNotIn(
            "permissionDecision", out, "正規化時に許可判断を握らないこと（権限境界を動かさない）"
        )

    def test_swarm_antigravity_task_is_converted_and_keeps_siblings(self):
        out = expect_decision(
            swarm(
                {
                    "backend": "antigravity",
                    "prompt": "P",
                    "workspace": str(ROOT),
                    "model": "M",
                }
            )
        )
        task = out["updatedInput"]["tasks"][0]
        self.assertTrue(task["workspace"].startswith("\\\\") or task["workspace"][1:3] == ":\\")
        self.assertEqual(task["prompt"], "P")
        self.assertEqual(task["model"], "M")
        self.assertEqual(task["backend"], "antigravity")

    def test_other_backend_windows_path_passes_unchanged(self):
        """契約未検証のバックエンドでも、既に Windows 絶対パスなら触らず通す。"""
        self.assertIsNone(
            run_guard(
                {
                    "tool_name": "mcp__agy__codex_ask",
                    "tool_input": {"workspace": r"C:\Users", "prompt": "x"},
                }
            )
        )


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestFailClose(unittest.TestCase):
    """検査できなかったときに素通しさせない（Codex 再レビュー BLOCKER）。

    非0終了は exit 2 以外ツール実行を止めないため、フックが落ちた・固まった場合に
    deny を返せないと、検証されていない入力のままツールが走ってしまう。
    """

    def _run_with_fake_python(self, script):
        d = tempfile.mkdtemp(prefix="fakepy_")
        try:
            fake = Path(d) / "python3"
            fake.write_text(script, encoding="utf-8")
            fake.chmod(0o755)
            env = dict(os.environ, PATH=f"{d}{os.pathsep}{os.environ['PATH']}")
            r = subprocess.run(
                [str(HOOK)], input=json.dumps(ask(prompt="x")), text=True,
                capture_output=True, check=True, env=env,
            )
            return json.loads(r.stdout)["hookSpecificOutput"]
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_interpreter_crash_is_denied(self):
        out = self._run_with_fake_python("#!/bin/sh\nexit 3\n")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("異常終了", out["permissionDecisionReason"])

    def test_interpreter_hang_is_denied(self):
        out = self._run_with_fake_python("#!/bin/sh\nsleep 60\n")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("期限", out["permissionDecisionReason"])


@unittest.skipUnless(_HAS_BASH, "bash が必要")
class TestUnknownTool(unittest.TestCase):
    def test_unknown_agy_tool_is_denied(self):
        """将来 workspace を取るツールが増えたとき、列挙漏れで素通ししない。"""
        out = expect_decision({"tool_name": "mcp__agy__future_tool", "tool_input": {"foo": 1}})
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("未知", out["permissionDecisionReason"])

    def test_other_backend_linux_path_is_denied(self):
        """契約未検証のバックエンドに Linux パスを渡したら、推測変換せず deny する。"""
        out = expect_decision(
            {
                "tool_name": "mcp__agy__codex_ask",
                "tool_input": {"workspace": str(ROOT), "prompt": "x"},
            }
        )
        self.assertEqual(out["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
