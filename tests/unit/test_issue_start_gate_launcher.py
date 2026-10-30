"""dispatch gate の起動口が検査面（cwd）のコードを実行しないことを実 hook 起動で固定する（#685 F-685-22）。"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / ".claude" / "hooks" / "issue-start-gate.sh"
UNMANAGED = {"tool_name": "Agent", "tool_input": {"subagent_type": "Explore", "prompt": "x"}}
MANAGED = {"tool_name": "Agent", "tool_input": {"subagent_type": "ac-designer", "isolation": "worktree",
                                                "prompt": "x"}}


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "bash と git が要る")
class IssueStartGateLauncherTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.surface, self.marker = Path(temporary.name) / "surface", Path(temporary.name) / "marker"
        subprocess.run(["git", "init", "-q", str(self.surface)], check=True)

    def plant_shadow_modules(self, directory=None, stdlib=("json", "subprocess", "pathlib")):
        directory = self.surface if directory is None else directory
        source = f"open({str(self.marker)!r}, 'w').write('x')\nprint('SHADOW')\n"
        (directory / "issue_start").mkdir(parents=True)
        (directory / "issue_start" / "__init__.py").write_text("")
        (directory / "issue_start" / "hook.py").write_text(source)
        for module in stdlib:
            (directory / f"{module}.py").write_text(source)

    def launch(self, payload, **overrides):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT), **overrides}
        env = {key: value for key, value in env.items() if value is not None}
        env.pop("PYTHONSAFEPATH", None)
        result = subprocess.run(["bash", str(LAUNCHER)], input=json.dumps(payload), text=True,
                                capture_output=True, cwd=self.surface, env=env, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("SHADOW", result.stdout + result.stderr)
        self.assertFalse(self.marker.exists(), "検査面の同名モジュールが実行された")
        return result

    def assert_trusted_gate_decides(self, **overrides):
        unmanaged = self.launch(UNMANAGED, **overrides)
        self.assertEqual(unmanaged.stdout, "")
        self.assertIn('"result":"UNMANAGED"', unmanaged.stderr.replace(" ", ""))
        denied = json.loads(self.launch(MANAGED, **overrides).stdout)["hookSpecificOutput"]
        self.assertEqual(denied["permissionDecision"], "deny")
        self.assertIn("ISSUE_START_BINDING_MISSING_OR_DUPLICATE", denied["permissionDecisionReason"])

    def test_normal_dispatch_path_reaches_the_trusted_gate(self):
        self.assert_trusted_gate_decides()

    def test_shadow_issue_start_and_stdlib_on_the_inspected_surface_are_not_imported(self):
        self.plant_shadow_modules()
        self.assert_trusted_gate_decides()

    def test_project_root_precedes_an_inherited_pythonpath_package(self):
        inherited = self.surface.parent / "inherited"
        self.plant_shadow_modules(inherited, stdlib=())
        self.assert_trusted_gate_decides(PYTHONPATH=str(inherited))

    def test_missing_project_dir_falls_back_to_the_launcher_root_not_the_surface(self):
        self.plant_shadow_modules()
        self.assert_trusted_gate_decides(CLAUDE_PROJECT_DIR=None)
