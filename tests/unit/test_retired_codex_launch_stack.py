"""Issue #538 PR-A: 退役した Codex 起動スタックの module 名と hook 名が active tree へ戻らないことの回帰。

検出するのは RETIRED_MODULE_AND_HOOK_NAMES に挙げた module 名と hook 名だけである。
退役スタックの runtime 識別子（state ディレクトリ名、profile 名、platform 値等）と、
それらの名前を含まない散文の残存は、このテストでは検出しない。
"""

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
# 検出語彙は module 名と hook 名に限る（Issue #538 F-538-04 のオーナー決定で広げない）。
# codex_supervisor_launch は module 名 codex_supervisor を含む manifest block 名である。
RETIRED_MODULE_AND_HOOK_NAMES = (
    "codex_supervisor",
    "codex_supervisor_launch",
    "codex_launch_intent",
    "codex_launch_control",
    "codex_karte_bridge",
    "codex-launch-intent-gate",
)
# 履歴として保全する置き場。退役した名前を記録として含んでよい（書き換えない）。
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


def _retired_module_and_hook_names_in(relative: str) -> list[str]:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        return []
    text = path.read_bytes().decode("utf-8", errors="ignore")
    return [name for name in RETIRED_MODULE_AND_HOOK_NAMES if name in text or name in relative]


class RetiredCodexLaunchStackTests(unittest.TestCase):
    def test_retired_modules_tests_and_hook_script_are_absent(self):
        remaining = [name for name in RETIRED_FILES if (ROOT / name).exists()]
        self.assertEqual(remaining, [])

    def test_retired_module_and_hook_names_do_not_reappear_in_active_tree(self):
        """module 名と hook 名の再出現だけを見る。runtime 識別子と散文の残存は対象外。"""
        hits = {
            relative: found
            for relative in _tracked_files()
            if _is_active(relative)
            for found in [_retired_module_and_hook_names_in(relative)]
            if found
        }
        self.assertEqual(hits, {}, "\n".join(sorted(hits)))


if __name__ == "__main__":
    unittest.main()
