"""直接編集 gate の登録コマンドが cwd のコードを実行しないことを実 hook 起動で固定する（#685 F-685-33）。"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests.unit.hook_launcher_support import ROOT, copy_project_with_spaces, registered_commands

READ_ONLY_DENY = "read-only工程では直接編集できません。"


@unittest.skipUnless(shutil.which("bash") and shutil.which("sh"), "bash と sh が要る")
class PhaseToolGateLauncherTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.cwd, self.marker = Path(temporary.name) / "cwd", Path(temporary.name) / "marker"
        self.cwd.mkdir()

    def plant_shadow_modules(self):
        source = f"open({str(self.marker)!r}, 'w').write('x')\nprint('SHADOW')\n"
        (self.cwd / "issue_start").mkdir()
        (self.cwd / "issue_start" / "__init__.py").write_text("")
        (self.cwd / "issue_start" / "phase_tool_gate.py").write_text(source)
        for module in ("json", "sys"):
            (self.cwd / f"{module}.py").write_text(source)

    def launch(self, tool, payload, **overrides):
        [command] = registered_commands(tool, "phase-tool-gate.sh")
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT), **overrides}
        env = {key: value for key, value in env.items() if value is not None}
        env.pop("PYTHONSAFEPATH", None)
        result = subprocess.run(["sh", "-c", command], input=payload, text=True, capture_output=True,
                                cwd=self.cwd, env=env, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("SHADOW", result.stdout + result.stderr)
        self.assertFalse(self.marker.exists(), "cwd の同名モジュールが実行された")
        return result.stdout

    def assert_trusted_gate_decides(self, **overrides):
        for tool in ("Write", "Edit", "NotebookEdit"):
            with self.subTest(tool=tool):
                for role in ("pr-reviewer", "plan-reviewer"):
                    denied = json.loads(self.launch(tool, json.dumps({"agent_type": role}), **overrides))
                    self.assertIn(READ_ONLY_DENY, denied["hookSpecificOutput"]["permissionDecisionReason"])
                for allowed in ({"agent_type": "test-writer"}, {"tool_name": tool}):
                    self.assertEqual(self.launch(tool, json.dumps(allowed), **overrides), "")
                invalid = json.loads(self.launch(tool, "[1]", **overrides))["hookSpecificOutput"]
                self.assertEqual(invalid["permissionDecision"], "deny")

    def test_normal_path_reaches_the_trusted_gate_from_a_cwd_without_issue_start(self):
        self.assert_trusted_gate_decides()

    def test_shadow_gate_and_stdlib_in_the_cwd_are_not_imported(self):
        self.plant_shadow_modules()
        self.assert_trusted_gate_decides()

    def test_registered_command_reaches_the_gate_under_a_project_root_with_spaces(self):
        # 登録行の "$CLAUDE_PROJECT_DIR" のクォートを外すと path が空白で割れ、exit 127（非ブロック）で素通しになる。
        self.assert_trusted_gate_decides(CLAUDE_PROJECT_DIR=str(copy_project_with_spaces(self.cwd.parent)))

    def test_missing_project_dir_falls_back_to_the_launcher_root_not_the_cwd(self):
        self.plant_shadow_modules()
        script = ROOT / ".claude" / "hooks" / "phase-tool-gate.sh"
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PROJECT_DIR", "PYTHONSAFEPATH")}
        result = subprocess.run(["bash", str(script)], input=json.dumps({"agent_type": "adviser"}), text=True,
                                capture_output=True, cwd=self.cwd, env=env, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(READ_ONLY_DENY, result.stdout)
        self.assertFalse(self.marker.exists())
