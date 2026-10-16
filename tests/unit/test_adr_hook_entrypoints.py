"""新規PostToolUse入口とtrust診断の回帰。"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from adr.store import write
from adr.notice_roots import register_root
from tests.unit.test_adr import draft
from tests.unit.codex_hook_trust_support import CodexHookTrustTestMixin

ROOT = Path(__file__).resolve().parents[2]


class AdrHookEntrypointTest(CodexHookTrustTestMixin, unittest.TestCase):
    def test_post_tool_hook_untrusted_status_is_reported(self):
        result = self._run_check("post-tool-untrusted")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("post_tool_use:0:0", result.stdout)
        self.assertIn("sha256:post-tool", result.stdout)
        self.assertNotIn("pre_tool_use:1:0", result.stdout)
        warning = self._run_hook("post-tool-untrusted")
        self.assertEqual(warning.returncode, 0)
        self.assertIn("post_tool_use:0:0", warning.stdout)

    def test_codex_entry_uses_repo_module_and_fails_open(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temporary:
            cwd = Path(temporary)
            (cwd / "adr").mkdir()
            (cwd / "adr/__init__.py").write_text("")
            (cwd / "adr/hook.py").write_text("raise RuntimeError('decoy import')")
            write(cwd / "records", draft())
            register_root(cwd / "records", cwd)
            payload = dict(tool_name="Bash", cwd=str(cwd), tool_input={
                "command": "python3 -m adr new-entry --root records --draft x"})
            script = ROOT / ".codex/hooks/adr-notify.sh"
            result = subprocess.run(["bash", str(script)], cwd=cwd, input=json.dumps(payload),
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(draft()["id"], json.loads(result.stdout)["systemMessage"])
            malformed = subprocess.run(["bash", str(script)], cwd=cwd, input="invalid JSON",
                                       capture_output=True, text=True, check=False)
            self.assertEqual(malformed.returncode, 0)
            self.assertEqual(malformed.stdout, "")
            self.assertIn("adr-notify:", malformed.stderr)
