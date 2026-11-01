"""PR base 取り込み（gitgate-base-integration/2.0・Issue #706）の実 Git 受け入れテスト。

bare remote と linked worktree / primary checkout を実際に作り、GitHub API だけを
読取専用の偽物に置き換える。ロール・dispatch 台帳・登録・テスト実行は一切用意しない。
"""

import copy
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from gitgate import base_cli, dispatch
from gitgate.base_error import BaseIntegrationError
from gitgate.base_git import git_path
from gitgate.base_request import parse_request
from gitgate.base_state import state_path

REPOSITORY = "example/repo"
PROTECTED = (".codex/config.toml", ".agents/skills/x/SKILL.md", ".claude/settings.json",
             ".ai/guidance/common.md", "AGENTS.md", "CLAUDE.md",
             ".github/copilot-instructions.md", ".ai/agents/issue-fixer.md")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True,
                          check=True).stdout.strip()


def write(root, name, text):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class PullApi:
    def __init__(self, head, base, head_ref="fix"):
        self.pull = {"number": 9, "state": "open",
                     "head": {"ref": head_ref, "sha": head, "repo": {"full_name": REPOSITORY}},
                     "base": {"ref": "main", "sha": base, "repo": {"full_name": REPOSITORY}}}
        self.default_branch = "main"

    def pull_request(self, repository, number):
        return copy.deepcopy(self.pull)

    def repository(self, repository):
        return {"default_branch": self.default_branch}


class Fixture(unittest.TestCase):
    """main に base 変更、fix に head 変更（item.txt が衝突）を持つ PR #9。"""

    base_files = {"item.txt": "base\n"}
    head_files = {"item.txt": "head\n"}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.main, self.remote = root / "main", root / "remote.git"
        self.main.mkdir()
        git(self.main, "init", "-b", "main")
        git(self.main, "config", "user.name", "Integration test")
        git(self.main, "config", "user.email", "integration@example.invalid")
        write(self.main, ".gitignore", ".worktrees/\nignored.log\n")
        for name in ("item.txt", "other.txt") + PROTECTED:
            write(self.main, name, "seed\n")
        git(self.main, "add", ".")
        git(self.main, "commit", "-m", "seed")
        git(root, "init", "--bare", str(self.remote))
        git(self.main, "remote", "add", "origin", "https://github.com/example/repo.git")
        git(self.main, "push", str(self.remote), "main")
        git(self.main, "switch", "-c", "fix")
        self.commit_files(self.head_files, "head change")
        self.head = git(self.main, "rev-parse", "HEAD")
        git(self.main, "push", str(self.remote), "fix")
        git(self.main, "switch", "main")
        self.commit_files(self.base_files, "base change")
        self.base = git(self.main, "rev-parse", "HEAD")
        git(self.main, "push", str(self.remote), "main")
        self.work = self.main / ".worktrees/pr-9"
        git(self.main, "worktree", "add", str(self.work), "fix")
        self.commands = []
        actual_run = subprocess.run
        def local_transport(command, **kwargs):
            command = list(command)
            self.commands.append(command)
            if command[0] == "git" and "origin" in command and "fetch" in command:
                command[command.index("origin")] = str(self.remote)
            return actual_run(command, **kwargs)
        transport = mock.patch("gitgate.base_git.subprocess.run", side_effect=local_transport)
        transport.start()
        self.addCleanup(transport.stop)
        self.api = PullApi(self.head, self.base)
        self.start_args = ["--repository", REPOSITORY, "--pr", "9", "--expected-head",
                           self.head, "--expected-base", self.base]

    def commit_files(self, files, message):
        for name, text in files.items():
            write(self.main, name, text)
        git(self.main, "add", ".")
        git(self.main, "commit", "-m", message)

    def execute(self, verb, args=(), workspace=None):
        return base_cli.execute(verb, list(args), workspace=workspace or self.work, api=self.api)

    def start(self, workspace=None):
        return self.execute("integrate-base", self.start_args, workspace)

    def continue_(self, workspace=None):
        return self.execute("integrate-base-continue", workspace=workspace)

    def abort(self, workspace=None):
        return self.execute("integrate-base-abort", workspace=workspace)

    def resolve(self, workspace=None):
        write(workspace or self.work, "item.txt", "resolved\n")

    def assert_committed(self, result, workspace=None):
        workspace = workspace or self.work
        self.assertEqual(result["status"], "committed")
        self.assertEqual(result["parents"], [self.head, self.base])
        self.assertEqual(git(workspace, "rev-parse", "HEAD^{tree}"), result["tree"])
        self.assertEqual(git(workspace, "status", "--porcelain"), "")
        self.assertFalse(state_path(workspace).exists())
        self.assertFalse(any("unittest" in part for command in self.commands for part in command))


class IntegrationFlowTests(Fixture):
    def test_conflict_resolve_continue_without_tests_or_dispatch(self):
        result = self.start()
        self.assertEqual(result, {"status": "conflicts", "conflicts": ["item.txt"]})
        self.resolve()
        self.assert_committed(self.continue_())
        self.assertEqual(git(self.work, "show", "HEAD:item.txt"), "resolved")

    def test_continue_cli_rejects_test_module_option(self):
        with self.assertRaisesRegex(BaseIntegrationError, "ARGUMENT_INVALID"):
            parse_request("integrate-base-continue", ["--test-module", "tests.unit.x"])
        with self.assertRaisesRegex(BaseIntegrationError, "VERB_INVALID"):
            parse_request("integrate-base-copilot-register", self.start_args)

    def test_primary_worktree_checkout_can_integrate(self):
        git(self.main, "worktree", "remove", str(self.work))
        git(self.main, "switch", "fix")
        self.assertEqual(self.start(self.main)["status"], "conflicts")
        self.resolve(self.main)
        self.assert_committed(self.continue_(self.main), self.main)

    def test_subdirectory_cwd_resolves_to_checkout_root(self):
        (self.work / "sub").mkdir()
        self.assertEqual(self.start(self.work / "sub")["status"], "conflicts")

    def test_extra_tracked_new_and_generated_files_are_committed_when_staged(self):
        self.start()
        self.resolve()
        write(self.work, "other.txt", "adjusted around the conflict\n")
        write(self.work, "generated/out.txt", "regenerated\n")
        dispatch_add = ["add", "other.txt", "generated/out.txt"]
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.work)
        self.assertEqual(dispatch.main(dispatch_add), 0)
        self.assert_committed(self.continue_())
        self.assertEqual(git(self.work, "show", "HEAD:generated/out.txt"), "regenerated")
        self.assertEqual(git(self.work, "show", "HEAD:other.txt"), "adjusted around the conflict")

    def test_unstaged_leftovers_stop_and_keep_pending_work(self):
        self.start()
        self.resolve()
        write(self.work, "other.txt", "forgot to stage\n")
        write(self.work, "new.txt", "forgot to stage\n")
        with self.assertRaisesRegex(BaseIntegrationError, "UNSTAGED_CHANGES_REMAIN: new.txt, other.txt"):
            self.continue_()
        self.assertEqual(git_path(self.work, "MERGE_HEAD").read_text().strip(), self.base)
        self.assertEqual((self.work / "other.txt").read_text(), "forgot to stage\n")
        git(self.work, "add", "other.txt", "new.txt")
        self.assert_committed(self.continue_())

    def test_ignored_files_do_not_block(self):
        self.start()
        self.resolve()
        write(self.work, "ignored.log", "local noise\n")
        self.assert_committed(self.continue_())

    def test_unresolved_conflict_markers_are_rejected(self):
        self.start()
        with self.assertRaisesRegex(BaseIntegrationError, "CONFLICT_MARKERS_STOP: item.txt"):
            self.continue_()
        self.assertNotEqual(git(self.work, "ls-files", "--unmerged"), "")
        self.resolve()
        self.assert_committed(self.continue_())

    def test_abort_saves_edits_restores_head_without_api(self):
        self.start()
        self.resolve()
        write(self.work, "untracked.txt", "valuable new file\n")
        with mock.patch.object(self.api, "pull_request", side_effect=AssertionError("no API")):
            result = self.abort()
        self.assertEqual(result["status"], "aborted")
        with tarfile.open(result["recovery"]) as archive:
            self.assertEqual(archive.extractfile("worktree/item.txt").read(), b"resolved\n")
            self.assertEqual(archive.extractfile("worktree/untracked.txt").read(),
                             b"valuable new file\n")
            self.assertEqual(archive.extractfile("git/MERGE_HEAD").read().strip(),
                             self.base.encode())
        self.assertTrue(Path(result["recovery"]).is_relative_to(self.main / ".git"))
        self.assertEqual(git(self.work, "rev-parse", "HEAD"), self.head)
        self.assertFalse(state_path(self.work).exists())
        self.assertEqual((self.work / "untracked.txt").read_text(), "valuable new file\n")
        (self.work / "untracked.txt").unlink()
        self.assertEqual(self.start()["status"], "conflicts")

    def test_abort_clears_stale_record_after_merge_ended_outside(self):
        self.start()
        git(self.work, "merge", "--abort")
        with self.assertRaisesRegex(BaseIntegrationError, "PENDING_COMMIT_DENIED"):
            base_cli.refuse_pending_commit(self.work)
        self.assertEqual(self.abort()["status"], "cleared")
        base_cli.refuse_pending_commit(self.work)


class SimpleMergeTests(Fixture):
    head_files = {"head.txt": "head\n"}
    base_files = {**{name: "base contract\n" for name in PROTECTED}, "added.txt": "new\n"}

    def test_protected_paths_incoming_merge_and_no_change(self):
        self.assertEqual(self.start(), {"status": "ready", "conflicts": []})
        result = self.continue_()
        self.assert_committed(result)
        for name in PROTECTED:
            self.assertEqual(git(self.work, "show", f"HEAD:{name}"), "base contract")
        git(self.work, "push", str(self.remote), "fix")
        self.api.pull["head"]["sha"] = self.start_args[-3] = result["oid"]
        self.assertEqual(self.start()["status"], "no_change")
        self.assertFalse(state_path(self.work).exists())


class ProtectedConflictTests(Fixture):
    head_files = {name: "head contract\n" for name in PROTECTED}
    base_files = {name: "base contract\n" for name in PROTECTED}

    def test_conflicting_protected_paths_can_be_resolved(self):
        self.assertEqual(self.start()["conflicts"], sorted(PROTECTED))
        for name in PROTECTED:
            write(self.work, name, "merged contract\n")
        self.assert_committed(self.continue_())
        for name in PROTECTED:
            self.assertEqual(git(self.work, "show", f"HEAD:{name}"), "merged contract")


if __name__ == "__main__":
    unittest.main()
