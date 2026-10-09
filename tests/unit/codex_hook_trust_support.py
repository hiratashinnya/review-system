"""Process helpers shared by Codex hook trust tests."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from tests.unit.codex_hook_trust_fake_server import make_fake_codex
from tests.unit.codex_hook_trust_repo_support import make_project_repository

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude/hooks/codex-hook-trust-check.sh"


class CodexHookTrustTestMixin:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.codex = make_fake_codex(self.temp.name)
        self.repo = make_project_repository(Path(self.temp.name), ROOT)

    def tearDown(self):
        self.temp.cleanup()

    def _run_check(self, mode="trusted", *options, repo=None, executable=None):
        return run_check(
            executable or self.codex, mode, *options, repo=repo or self.repo,
        )

    def _run_hook(self, mode="trusted", *, repo=None, executable=None, extra_env=None):
        return run_hook(
            executable or self.codex, mode, repo=repo or self.repo, extra_env=extra_env,
        )


def _environment(executable, mode, extra_env=None):
    env = dict(os.environ)
    env.update(CODEX_HOOK_TRUST_CODEX=str(executable), FAKE_CODEX_MODE=mode)
    temporary_root = env.get("TMPDIR")
    if temporary_root:
        env["GIT_CEILING_DIRECTORIES"] = str(Path(temporary_root).resolve())
    env.update(extra_env or {})
    return env


def configured_hook_count(repo):
    """Count configured handlers independently from the CLI implementation."""
    config_path = repo / ".codex" / "hooks.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return sum(
        len(group["hooks"])
        for event_groups in config["hooks"].values()
        for group in event_groups
    )


def hook_count_report(repo, discovered_count):
    return (
        f"定義 {configured_hook_count(repo)} 件に対し"
        f"発見 {discovered_count} 件"
    )


def one_missing_hook_report(repo):
    return hook_count_report(repo, configured_hook_count(repo) - 1)


def run_check(executable, mode="trusted", *options, repo=ROOT, extra_env=None):
    return subprocess.run(
        [sys.executable, "-m", "codex_hook_trust", "check", "--repo", str(repo),
         *options], cwd=ROOT, capture_output=True, text=True, timeout=5,
        env=_environment(executable, mode, extra_env), check=False,
    )


def run_hook(executable, mode="trusted", *, repo=ROOT, extra_env=None):
    env = _environment(executable, mode, extra_env)
    env.update(CLAUDE_PROJECT_DIR=str(repo), PYTHONPATH=str(ROOT))
    return subprocess.run(
        ["bash", str(HOOK)], input='{"session_id":"payload-must-be-discarded"}',
        capture_output=True, text=True, timeout=25, env=env, check=False,
    )
