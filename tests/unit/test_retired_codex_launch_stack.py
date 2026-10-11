"""Issue #538 PR-A: 退役した Codex 起動スタックが active tree へ戻らないことの回帰。"""

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve().relative_to(ROOT).as_posix()
RETIRED_FILES = (
    "issue_start/codex_supervisor.py",
    "issue_start/codex_launch_intent.py",
    "issue_start/codex_launch_control.py",
    "issue_start/codex_supervisor_workspace.py",
    "issue_start/codex_karte_bridge.py",
    "tests/unit/test_codex_supervisor.py",
    "tests/unit/test_codex_supervisor_shrink.py",
    "tests/unit/test_codex_launch_control.py",
    "tests/unit/test_codex_karte_bridge.py",
    ".codex/hooks/codex-launch-intent-gate.sh",
)
RETIRED_IDENTIFIERS = (
    "codex_supervisor",
    "codex_supervisor_launch",
    "codex_launch_intent",
    "codex_launch_control",
    "codex_karte_bridge",
    "codex-launch-intent-gate",
)
# 履歴として保全する置き場。退役した識別子を記録として含んでよい（書き換えない）。
HISTORY_ROOTS = (
    "archive/",
    "audit/",
    ".ai/rationale/",
    "jev_hooks/verify/",
    "tests/logs/",
    "tests/reports/",
)


def _tracked_files() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True,
    )
    return [name for name in listed.stdout.decode("utf-8").split("\0") if name]


def _is_active(relative: str) -> bool:
    return relative != SELF and not relative.startswith(HISTORY_ROOTS)


def _retired_identifiers_in(relative: str) -> list[str]:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        return []
    text = path.read_bytes().decode("utf-8", errors="ignore")
    return [name for name in RETIRED_IDENTIFIERS if name in text or name in relative]


class RetiredCodexLaunchStackTests(unittest.TestCase):
    def test_retired_modules_tests_and_hook_script_are_absent(self):
        remaining = [name for name in RETIRED_FILES if (ROOT / name).exists()]
        self.assertEqual(remaining, [])

    def test_retired_identifiers_do_not_reappear_in_active_tree(self):
        hits = {
            relative: found
            for relative in _tracked_files()
            if _is_active(relative)
            for found in [_retired_identifiers_in(relative)]
            if found
        }
        self.assertEqual(hits, {}, "\n".join(sorted(hits)))


if __name__ == "__main__":
    unittest.main()
