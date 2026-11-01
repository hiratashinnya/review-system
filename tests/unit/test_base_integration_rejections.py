"""PR base 取り込みの取り違え・Git 状態破壊を拒否する検査（Issue #706）の実 Git テスト。"""

import os
import unittest
from unittest import mock

from gitgate import dispatch
from gitgate.base_error import BaseIntegrationError
from gitgate.base_git import git_path
from gitgate.base_request import parse_request
from gitgate.base_state import load, state_path, update
from tests.unit.test_base_integration import Fixture, REPOSITORY, git, write


class TargetRejectionTests(Fixture):
    def assert_rejected(self, pattern, workspace=None):
        before = git(workspace or self.work, "rev-parse", "HEAD")
        with self.assertRaisesRegex(BaseIntegrationError, pattern):
            self.start(workspace)
        self.assertEqual(git(workspace or self.work, "rev-parse", "HEAD"), before)
        self.assertIsNone(load(workspace or self.work))
        self.assertFalse(git_path(workspace or self.work, "MERGE_HEAD").exists())

    def test_default_branch_as_target_is_rejected(self):
        self.api.pull["head"].update(ref="main", sha=self.base)
        self.api.pull["base"]["ref"] = "release"
        self.start_args[-3] = self.base
        self.assert_rejected("DEFAULT_BRANCH_DENIED", self.main)
        self.api = type(self.api)(self.head, self.base)
        self.start_args[-3] = self.head
        self.api.default_branch = "fix"
        self.assert_rejected("DEFAULT_BRANCH_DENIED")

    def test_wrong_pr_head_base_and_repository_are_rejected(self):
        cases = [(("number",), 99, "PR_NOT_OPEN"), (("state",), "closed", "PR_NOT_OPEN"),
                 (("head", "ref"), "other", "HEAD_BRANCH_MISMATCH"),
                 (("base", "ref"), "fix", "HEAD_BRANCH_MISMATCH"),
                 (("head", "sha"), "a" * 40, "LIVE_OID_MISMATCH"),
                 (("base", "sha"), "b" * 40, "LIVE_OID_MISMATCH")]
        for keys, value, pattern in cases:
            with self.subTest(keys=keys):
                self.api = type(self.api)(self.head, self.base)
                target = self.api.pull
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                self.assert_rejected(pattern)
        self.api = type(self.api)(self.head, self.base)
        self.api.pull["head"]["repo"]["full_name"] = "fork/repo"
        self.assert_rejected("FORK")
        self.api.pull["head"]["repo"]["full_name"] = REPOSITORY
        self.start_args[1] = "other/repo"
        self.assert_rejected("REPOSITORY_MISMATCH")

    def test_expected_head_must_match_checkout_and_base_must_match_fetch(self):
        self.start_args[-3] = self.base
        self.assert_rejected("HEAD_OID_MISMATCH")
        self.start_args[-3] = self.head
        self.api.pull["base"]["sha"] = self.start_args[-1] = self.head
        self.assert_rejected("FETCH_OID_MISMATCH")

    def test_dirty_detached_and_competing_operations_are_rejected(self):
        write(self.work, "other.txt", "dirty\n")
        self.assert_rejected("NOT_CLEAN")
        git(self.work, "restore", "other.txt")
        write(self.work, "scratch.txt", "untracked\n")
        self.assert_rejected("NOT_CLEAN")
        (self.work / "scratch.txt").unlink()
        git_path(self.work, "CHERRY_PICK_HEAD").write_text(self.base)
        self.assert_rejected("NOT_CLEAN")
        git_path(self.work, "CHERRY_PICK_HEAD").unlink()
        git(self.work, "switch", "--detach")
        with self.assertRaisesRegex(BaseIntegrationError, "DETACHED_HEAD"):
            self.start()

    def test_api_failure_leaves_clean_tree_without_record(self):
        with mock.patch.object(self.api, "pull_request", side_effect=RuntimeError("offline")):
            with self.assertRaises(RuntimeError):
                self.start()
        self.assertEqual(git(self.work, "status", "--porcelain"), "")
        self.assertIsNone(load(self.work))

    def test_option_injection_rejected(self):
        for args in (["--strategy", "ours"], ["--repository", REPOSITORY],
                     self.start_args + ["--pr", "10"]):
            with self.assertRaises(BaseIntegrationError):
                parse_request("integrate-base", args)
        with self.assertRaises(BaseIntegrationError):
            parse_request("integrate-base-abort", ["--force"])


class PendingRejectionTests(Fixture):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.start()["status"], "conflicts")
        self.resolve()

    def test_double_start_is_rejected(self):
        with self.assertRaisesRegex(BaseIntegrationError, "OPERATION_PENDING"):
            self.start()

    def test_base_moved_or_pr_retargeted_during_resolution_is_rejected(self):
        for field, value in (("sha", "c" * 40), ("ref", "release")):
            with self.subTest(field=field):
                original = self.api.pull["base"][field]
                self.api.pull["base"][field] = value
                with self.assertRaises(BaseIntegrationError):
                    self.continue_()
                self.api.pull["base"][field] = original
                self.assertEqual(git_path(self.work, "MERGE_HEAD").read_text().strip(), self.base)
        self.assert_committed(self.continue_())

    def test_unmerged_index_outside_record_is_rejected(self):
        record = load(self.work)
        update(self.work, {**{k: v for k, v in record.items() if k != "policy_version"},
                           "conflicts": []})
        with self.assertRaisesRegex(BaseIntegrationError, "UNRESOLVED_INDEX: item.txt"):
            self.continue_()

    def test_competing_git_operation_or_moved_head_is_rejected(self):
        (git_path(self.work, "rebase-merge")).mkdir()
        for verb in (self.continue_, self.abort):
            with self.assertRaisesRegex(BaseIntegrationError, "PENDING_MERGE_STATE_INVALID"):
                verb()
        (git_path(self.work, "rebase-merge")).rmdir()
        git_path(self.work, "MERGE_HEAD").write_text(self.head + "\n")
        for verb in (self.continue_, self.abort):
            with self.assertRaisesRegex(BaseIntegrationError, "PENDING_MERGE_STATE_INVALID"):
                verb()
        self.assertEqual((self.work / "item.txt").read_text(), "resolved\n")

    def test_ordinary_commit_is_fenced_while_pending(self):
        message = self.work / ".git-message"
        message.write_text("manual")
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.work)
        self.assertEqual(dispatch.main(["commit", str(message)]), 2)
        self.assertEqual(git(self.work, "rev-parse", "HEAD"), self.head)


class ForeignMergeTests(Fixture):
    def test_merge_not_started_by_gitgate_is_never_continued_or_aborted(self):
        git(self.work, "fetch", str(self.remote), "main")
        subprocess_merge = git(self.work, "rev-parse", "FETCH_HEAD")
        with self.assertRaises(Exception):
            git(self.work, "merge", "--no-commit", subprocess_merge)
        for verb in (self.continue_, self.abort):
            with self.assertRaisesRegex(BaseIntegrationError, "OPERATION_MISSING"):
                verb()
        self.assertEqual(git_path(self.work, "MERGE_HEAD").read_text().strip(), self.base)
        self.assertFalse(state_path(self.work).exists())
        with self.assertRaisesRegex(BaseIntegrationError, "NOT_CLEAN"):
            self.start()


if __name__ == "__main__":
    unittest.main()
