"""後続作者dispatchの検査面と別worktreeのadopt-branchの関係を実gitで固定する（#685）。

detachedなら検査を通りadoptも成功し、対象branchを掴んだままなら検査が入口で拒否する。"""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from branch_source import BranchSourceError
from gitgate.adopt import AdoptBranchRequest, adopt_branch
from issue_start.gate_support import IssueStartError
from tests.unit.codex_worktree_exec_support import git
from tests.unit import test_phase_target_binding as binding_fixture


class PhaseTargetAdoptCoexistenceTests(unittest.TestCase):
    def setUp(self):
        self.case = binding_fixture.PhaseTargetBindingTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root, oid = self.case.root, self.case.native["expected_oid"]
        main = Path(git(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir")).parent
        bare = main.parent / "origin.git"
        git(main.parent, "init", "-q", "--bare", str(bare))
        git(self.root, "push", "-q", str(bare), f"{oid}:refs/heads/agent/test")
        self.author = main.parent / "author"
        git(main, "worktree", "add", "-q", "-b", "worktree-author", str(self.author), oid)
        self.request = AdoptBranchRequest(branch_name="agent/test", repository="owner/repo", expected_oid=oid)
        self.origin_env = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": f"url.{bare}.insteadOf",
                           "GIT_CONFIG_VALUE_0": "https://github.com/owner/repo.git"}

    def adopt(self):
        with patch.dict(os.environ, self.origin_env):
            return adopt_branch(self.request, cwd=self.author)

    def test_detached_dispatch_source_passes_gate_and_author_adopts_same_oid(self):
        git(self.root, "switch", "-q", "--detach", "HEAD")
        self.assertEqual(self.case.parse().issue, 371)
        self.assertEqual(self.adopt().expected_oid, self.request.expected_oid)
        self.assertEqual(git(self.author, "symbolic-ref", "--short", "HEAD"), "agent/test")
        self.assertEqual(git(self.author, "rev-parse", "HEAD"), self.request.expected_oid)

    def test_dispatch_source_holding_the_branch_is_rejected_by_the_gate_before_adopt(self):
        with self.assertRaises(IssueStartError) as gate:
            self.case.parse()
        self.assertEqual(gate.exception.reason, "ISSUE_START_PHASE_TARGET_INVALID")
        self.assertIn(f"git switch --detach {self.request.expected_oid}", str(gate.exception))
        with self.assertRaises(BranchSourceError) as adopt:
            self.adopt()
        self.assertEqual(adopt.exception.reason, "BRANCH_ADOPT_LOCAL_EXISTS")

    def test_non_agent_linked_holder_gets_detach_remedy_not_worktree_release(self):
        git(self.root, "switch", "-q", "--detach", "HEAD")
        main = Path(git(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir")).parent
        surface = main / ".claude" / "worktrees" / "review-685"
        git(main, "worktree", "add", "-q", str(surface), "agent/test")
        with self.assertRaises(BranchSourceError) as adopt:
            self.adopt()
        detail = str(adopt.exception)
        self.assertEqual(adopt.exception.reason, "BRANCH_ADOPT_LOCAL_EXISTS")
        self.assertIn(f"linked worktree {surface}", detail)
        self.assertIn("git switch --detach", detail)
        self.assertNotIn("--force-uncollected", detail)
        self.assertIn("同じブランチでは継続できない", detail)
