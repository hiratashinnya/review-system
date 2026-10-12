"""codex_worktree_exec のテスト用に、使い捨ての Git リポジトリと偽の codex を用意する。

実物の `codex` は起動しない（モデルを呼ばない model-free テスト）。実起動の検証は
`tests/designs/TD-codex-worktree-exec-538-001.md` に従い主文脈が検証専用環境で行う。
"""

import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PROFILE_SOURCE = ROOT / ".codex" / "config.toml"
GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Codex Exec Test",
    "GIT_AUTHOR_EMAIL": "codex-exec-test@example.invalid",
    "GIT_COMMITTER_NAME": "Codex Exec Test",
    "GIT_COMMITTER_EMAIL": "codex-exec-test@example.invalid",
}
FAKE_CODEX = """#!/bin/sh
printf '%s\\n' "$@" > "$FAKE_CODEX_LOG.argv"
cat > "$FAKE_CODEX_LOG.stdin"
env > "$FAKE_CODEX_LOG.env"
if [ -n "$FAKE_CODEX_SLEEP" ]; then exec sleep "$FAKE_CODEX_SLEEP"; fi
exit "${FAKE_CODEX_EXIT:-0}"
"""


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, env=GIT_ENV, check=False,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def make_repository(directory: Path, profile: str | None = None) -> tuple[Path, Path]:
    """main checkout と、その配下の linked worktree を作る。origin/main は profile の commit を指す。"""
    main = directory / "main"
    main.mkdir()
    git(main, "init", "-q")
    config = main / ".codex" / "config.toml"
    config.parent.mkdir()
    text = PROFILE_SOURCE.read_text(encoding="utf-8") if profile is None else profile
    config.write_text(text, encoding="utf-8")
    git(main, "add", ".codex/config.toml")
    git(main, "commit", "-q", "-m", "permission profile")
    git(main, "update-ref", "refs/remotes/origin/main", "HEAD")
    worktree = main / ".claude" / "worktrees" / "agent-test"
    git(main, "worktree", "add", "-q", "-b", "agent/test", str(worktree), "HEAD")
    return main.resolve(), worktree.resolve()


def add_worktree(main: Path, name: str) -> Path:
    worktree = main / ".claude" / "worktrees" / name
    git(main, "worktree", "add", "-q", "-b", f"agent/{name}", str(worktree), "HEAD")
    return worktree.resolve()


def write_trust(home: Path, project: Path, level: str = "trusted") -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.toml").write_text(
        f"[projects.{json.dumps(str(project))}]\ntrust_level = {json.dumps(level)}\n",
        encoding="utf-8",
    )


def make_fake_codex(directory: Path) -> Path:
    script = directory / "fake-codex"
    script.write_text(FAKE_CODEX, encoding="utf-8")
    script.chmod(0o755)
    return script


def clean_environ(**extra: str) -> dict:
    """Codex の内側で動いている印を持たない環境変数を返す。"""
    environ = {key: value for key, value in os.environ.items() if not key.startswith("CODEX_")}
    environ.update(extra)
    return environ
