"""karte-stop-once.sh: interpreter failures exit 0 with a log; hook output passes through."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests.unit.hook_launcher_support import ROOT

SCRIPT = ROOT / ".claude" / "hooks" / "karte-stop-once.sh"


@unittest.skipUnless(shutil.which("bash"), "bash is required")
class KarteStopOnceLauncherTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.bin = Path(temporary.name)

    def fake_python(self, body):
        path = self.bin / "python3"
        path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        path.chmod(0o755)

    def launch(self, *args, fake=True):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONSAFEPATH"}
        env["CLAUDE_PROJECT_DIR"] = str(ROOT)
        if fake:
            env["PATH"] = f"{self.bin}{os.pathsep}{env['PATH']}"
        return subprocess.run(["bash", str(SCRIPT), *args], input="{}", text=True,
                              capture_output=True, env=env, timeout=60)

    def test_interpreter_startup_failure_exits_zero_and_logs(self):
        self.fake_python("echo 'unknown option -P' >&2; exit 2")
        result = self.launch("pre")
        self.assertEqual(result.returncode, 0)
        self.assertIn("karte-stop-once: python3 exited with 2", result.stderr)

    def test_hook_json_output_passes_through(self):
        self.fake_python("echo '{\"permissionDecision\": \"deny\"}'")
        result = self.launch("pre")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), '{"permissionDecision": "deny"}')

    def test_output_is_kept_when_the_interpreter_then_fails(self):
        self.fake_python("echo '{\"a\": 1}'; exit 2")
        result = self.launch("pre")
        self.assertEqual((result.returncode, result.stdout.strip()), (0, '{"a": 1}'))

    def test_missing_argument_exits_zero_with_log(self):
        result = self.launch(fake=False)
        self.assertEqual(result.returncode, 0)
        self.assertIn("karte-stop-once:", result.stderr)

    def test_real_interpreter_ignores_a_non_target_payload(self):
        result = self.launch("post", fake=False)
        self.assertEqual((result.returncode, result.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
