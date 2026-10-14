"""F-538-32：許可名だけを偽 Codex の子環境へ渡す（モデルは呼ばない）。"""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from codex_worktree_exec.child_environment import build_codex_child_environment
from codex_worktree_exec.launcher import run_codex
from codex_worktree_exec.nesting_guard import NESTING_MARKER
from tests.unit.codex_worktree_exec_support import clean_environ, make_fake_codex

ALLOWED_NAMES = (
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "LC_ALL", "LC_CTYPE",
    "TERM", "TZ", "TMPDIR", "TEMP", "TMP", "CODEX_HOME",
    "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
)
FORBIDDEN_NAMES = (
    "CLAUDE_CODE_MESSAGING_TOKEN", "GH_TOKEN", "ANTHROPIC_API_KEY", "GITHUB_TOKEN",
    "OPENAI_API_KEY", "APP_TOKEN", "APP_KEY", "APP_SECRET", "APP_PASSWORD",
    "APP_CREDENTIAL", "CLAUDE_CONFIG_DIR", "ANTHROPIC_BASE_URL", "GH_HOST",
    "GITHUB_ACTIONS", "OPENAI_BASE_URL", "UNLISTED_VARIABLE",
)


class ChildEnvironmentTests(unittest.TestCase):
    def test_only_allowlisted_names_and_the_wrapper_marker_reach_popen(self):
        allowed = {name: f"fixture-{name}" for name in ALLOWED_NAMES}
        environ = {**allowed, **dict.fromkeys(FORBIDDEN_NAMES, "nonsecret-fixture")}
        process = Mock(returncode=0)
        with patch("codex_worktree_exec.launcher.subprocess.Popen", return_value=process) as popen:
            self.assertEqual(run_codex(
                ["codex", "exec", "-"], "依頼", cwd=Path("/w"),
                timeout_seconds=5, environ=environ,
            ), 0)
        self.assertEqual(popen.call_args.kwargs["env"], {**allowed, NESTING_MARKER: "1"})
        self.assertEqual(environ, {**allowed, **dict.fromkeys(FORBIDDEN_NAMES, "nonsecret-fixture")})

    def test_empty_input_does_not_inherit_the_parent_environment(self):
        with patch.dict("os.environ", {"GH_TOKEN": "nonsecret-fixture"}):
            self.assertEqual(build_codex_child_environment({}), {NESTING_MARKER: "1"})

    def test_wrapper_sets_its_own_nesting_marker(self):
        self.assertEqual(build_codex_child_environment({NESTING_MARKER: "0"}), {NESTING_MARKER: "1"})

    def test_real_child_keeps_startup_environment_and_excludes_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            codex = make_fake_codex(directory)
            environ = clean_environ(
                HOME=str(directory), CODEX_HOME=str(directory / "codex-home"),
                **dict.fromkeys(FORBIDDEN_NAMES, "nonsecret-fixture"),
            )
            self.assertEqual(run_codex(
                [str(codex), "exec", "-"], "依頼", cwd=directory,
                timeout_seconds=5, environ=environ,
            ), 0)
            child = dict(line.split("=", 1) for line in
                         (directory / "call.env").read_text(encoding="utf-8").splitlines())
            for name in ("PATH", "HOME", "CODEX_HOME"):
                self.assertEqual(child[name], environ[name])
            self.assertEqual(child[NESTING_MARKER], "1")
            self.assertFalse(set(FORBIDDEN_NAMES) & child.keys())
            self.assertFalse(any(word in name.upper() for name in child
                                 for word in ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")))


if __name__ == "__main__":
    unittest.main()
