"""Regression checks for the compatibility facade extracted in Issue #757."""

import unittest

from gitgate import worktree
from gitgate import worktree_arg_common
from gitgate import worktree_arg_lifecycle
from gitgate import worktree_arg_release
from gitgate import worktree_git_records
from gitgate import worktree_git_runtime
from gitgate import worktree_handoff_paths
from gitgate import worktree_models
from gitgate import worktree_path_validation


class WorktreeFacadeTests(unittest.TestCase):
    def test_public_types_keep_their_identity(self):
        for name in (
            "WorktreeError", "ReleaseRequest", "CollectRequest", "ForgetRequest",
            "SweepRequest", "SweepEntryOutcome", "ReleaseOutcome", "CollectOutcome",
        ):
            with self.subTest(name=name):
                self.assertIs(getattr(worktree, name), getattr(worktree_models, name))

    def test_parsers_keep_their_original_import_paths(self):
        for name, module in (
            ("parse_worktree_release_args", worktree_arg_release),
            ("parse_collect_worktree_args", worktree_arg_release),
            ("parse_worktree_forget_args", worktree_arg_lifecycle),
            ("parse_worktree_sweep_args", worktree_arg_lifecycle),
            ("_parse_flags", worktree_arg_common),
        ):
            with self.subTest(name=name):
                self.assertIs(getattr(worktree, name), getattr(module, name))

    def test_validation_and_git_helpers_keep_their_import_paths(self):
        for name, module in (
            ("validate_worktree_path", worktree_path_validation),
            ("resolve_within", worktree_path_validation),
            ("validate_handoff_relpath", worktree_handoff_paths),
            ("validate_collect_dest", worktree_handoff_paths),
            ("_run_git", worktree_git_runtime),
            ("_fetch_env", worktree_git_runtime),
            ("worktree_records", worktree_git_records),
            ("linked_worktree_paths", worktree_git_records),
            ("_is_git_managed", worktree_git_records),
        ):
            with self.subTest(name=name):
                self.assertIs(getattr(worktree, name), getattr(module, name))

    def test_error_category_and_argument_priority_stay_unchanged(self):
        with self.assertRaises(worktree.WorktreeError) as error:
            worktree.parse_worktree_release_args(
                [".claude/worktrees/agent-example", "--force-uncollected"]
            )
        self.assertEqual(error.exception.reason, "WORKTREE_REASON_EMPTY")
        with self.assertRaises(worktree.WorktreeError) as error:
            worktree.validate_worktree_path(".claude/worktrees/agent-x/../agent-y")
        self.assertEqual(error.exception.reason, "WORKTREE_PATH_PARENT_REF")


if __name__ == "__main__":
    unittest.main()
