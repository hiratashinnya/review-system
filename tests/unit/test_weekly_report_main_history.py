"""Fixed Git graphs for first-parent baseline measurements."""

import json
import os
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
import unittest

from weekly_report import history
from weekly_report.history_git import BASELINE_PATH
from weekly_report.period import parse_jst


def git(root, *args, env=None):
    return run(["git", "-C", str(root), *args], env=env, check=True,
               capture_output=True, text=True).stdout.strip()


def commit(root, when, *parents):
    git(root, "add", "--", ".")
    env = dict(os.environ, GIT_AUTHOR_NAME="Weekly Report", GIT_COMMITTER_NAME="Weekly Report",
               GIT_AUTHOR_EMAIL="weekly@example.test", GIT_COMMITTER_EMAIL="weekly@example.test",
               GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    parent_args = [token for parent in parents for token in ("-p", parent)]
    return git(root, "commit-tree", git(root, "write-tree"), *parent_args, "-m", "fixture", env=env)


def baseline(root, modules, blocks, mixed):
    target = root / BASELINE_PATH
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps({"schema_version": 2, "source": "fixture",
        "module_lines": {f"module{index}.py": {} for index in range(modules)},
        "comment_blocks": {"block.py|hash": blocks} if blocks else {},
        "mixed_class_files": {f"mixed{index}.py": {} for index in range(mixed)},
    }), encoding="utf-8")


class BaselineHistoryTests(unittest.TestCase):
    def test_first_parent_merge_boundary_and_dirty_checkout(self):
        with TemporaryDirectory() as location:
            root = Path(location)
            git(root, "init", "-q")
            (root / "README.md").write_text("fixture", encoding="utf-8")
            start = commit(root, "2025-01-01T10:00:00+09:00")
            baseline(root, 2, 3, 1)
            introduced = commit(root, "2025-01-02T10:00:00+09:00", start)
            baseline(root, 1, 0, 0)
            child = commit(root, "2025-01-03T10:00:00+09:00", introduced)
            merge_time = "2025-01-05T00:00:00+09:00"
            main_tip = commit(root, merge_time, introduced, child)
            baseline(root, 0, 0, 0)
            saved = json.loads(json.dumps(history.capture(root, main_tip)))
            old = history.measure(saved, parse_jst(merge_time))
            new = history.measure(saved, parse_jst("2025-01-05T00:00:01+09:00"))
            self.assertEqual(old["main_baseline_total"]["commit_sha"], introduced)
            self.assertEqual(old["main_baseline_total"]["value"], 6)
            self.assertEqual(old["main_baseline_comment_blocks"]["value"], 3)
            self.assertEqual(new["main_baseline_total"]["value"], 1)
            self.assertEqual(new["main_baseline_total"]["commit_sha"], main_tip)
            self.assertEqual(new["main_baseline_total"]["difference_from_initial"], -5)
            self.assertFalse(any(row["sha"] == child for row in saved["commits"]))

    def test_missing_ref_retains_unavailable_history(self):
        result = history.main_baseline(Path("/missing"), None, parse_jst("2025-01-05"))
        self.assertIsNone(result["main_baseline_total"]["value"])
        self.assertIn("基準 SHA", result["main_baseline_total"]["reason"])

    def test_backdated_descendant_cannot_enter_before_first_parent(self):
        with TemporaryDirectory() as location:
            root = Path(location)
            git(root, "init", "-q")
            baseline(root, 1, 0, 0)
            start = commit(root, "2025-01-03T10:00:00+09:00")
            baseline(root, 0, 0, 0)
            last = commit(root, "2025-01-02T10:00:00+09:00", start)
            result = history.main_baseline(root, last, parse_jst("2025-01-03"))
            self.assertIsNone(result["main_baseline_total"]["value"])

    def test_baseline_removed_in_first_parent_is_unknown_for_later_week(self):
        with TemporaryDirectory() as location:
            root = Path(location)
            git(root, "init", "-q")
            baseline(root, 1, 0, 0)
            start = commit(root, "2025-01-02T10:00:00+09:00")
            (root / BASELINE_PATH).unlink()
            last = commit(root, "2025-01-03T10:00:00+09:00", start)
            result = history.main_baseline(root, last, parse_jst("2025-01-04"))["main_baseline_total"]
            self.assertEqual(result["commit_sha"], last)
            self.assertIsNone(result["value"])
            self.assertEqual(result["initial"]["total"], 1)
