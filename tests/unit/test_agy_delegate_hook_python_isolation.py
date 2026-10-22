"""両 PF hook は cwd と PYTHONPATH の同名モジュールを実行しない。"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMAND = ("python3 -m agy_delegate run --workspace /tmp/work --settings /tmp/settings "
           "--executable /tmp/agy --prompt text --print-timeout 120 --caller-state ready")


class HookPythonIsolationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.untrusted = Path(temporary.name)
        self.marker = self.untrusted / "module-executed"
        source = f"open({str(self.marker)!r}, 'w').write('executed')\n"
        for module in ("json", "re", "shlex", "subprocess", "datetime", "sitecustomize"):
            (self.untrusted / f"{module}.py").write_text(source)

    def run_hook(self, platform, command, *, declared_cwd=None, process_cwd=None):
        body = {"agent_type": "agy-delegate", "tool_name": "exec_command",
                "tool_input": {"command": command}}
        if declared_cwd is not None:
            body["cwd"] = str(declared_cwd)
        environment = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT),
                       "PYTHONPATH": str(self.untrusted), "AGENT_COMMAND_GATE_TRACE_LOG": ""}
        result = subprocess.run(
            ["bash", str(ROOT / f".{platform}/hooks/agent-command-gate.sh")],
            input=json.dumps(body), text=True, capture_output=True, timeout=10,
            cwd=process_cwd or self.untrusted, env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertFalse(self.marker.exists())
        return json.loads(result.stdout) if result.stdout else None

    def test_untrusted_cwd_is_denied_without_executing_shadow_modules(self):
        for platform in ("claude", "codex"):
            with self.subTest(platform=platform):
                output = self.run_hook(platform, COMMAND)
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertIn("agy_delegate launch root", json.dumps(output))

    def test_explicit_trusted_launch_still_allowed_from_shadow_module_cwd(self):
        for platform in ("claude", "codex"):
            with self.subTest(platform=platform):
                self.assertIsNone(self.run_hook(platform, COMMAND, declared_cwd=ROOT))

    def test_trusted_cwd_ignores_pythonpath_and_keeps_allow_and_deny(self):
        for platform in ("claude", "codex"):
            with self.subTest(platform=platform):
                self.assertIsNone(self.run_hook(platform, COMMAND, process_cwd=ROOT))
                output = self.run_hook(platform, "agy -p text", process_cwd=ROOT)
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
