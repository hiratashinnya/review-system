"""後続作者dispatchの検査面と別worktreeのadopt-branchが実gitで両立することを固定する（#685）。"""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from branch_source import BranchSourceError
from gitgate.adopt import AdoptBranchRequest, adopt_branch
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

    def test_dispatch_source_holding_the_branch_still_blocks_adopt(self):
        self.assertEqual(self.case.parse().issue, 371)
        with self.assertRaises(BranchSourceError) as caught:
            self.adopt()
        self.assertEqual(caught.exception.reason, "BRANCH_ADOPT_LOCAL_EXISTS")
