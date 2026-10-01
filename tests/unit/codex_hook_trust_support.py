"""Process helpers shared by Codex hook trust tests."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude/hooks/codex-hook-trust-check.sh"


def _environment(executable, mode, extra_env=None):
    env = dict(os.environ)
    env.update(CODEX_HOOK_TRUST_CODEX=str(executable), FAKE_CODEX_MODE=mode)
    env.update(extra_env or {})
    return env


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
