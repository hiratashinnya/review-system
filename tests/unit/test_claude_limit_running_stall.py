"""handoff 無しで止まった role の entry は running に留まり、同じ role の再 dispatch は通らない（#829 F-847-r8-1）。"""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

from issue_start import subagent_hooks, worktree_ledger
from issue_start.author_continuation import MARKER, validate_author_continuation
from issue_start.gate_support import IssueStartError

ROOT = Path(__file__).resolve().parents[2]
FIXED_NOW = datetime(2026, 11, 17, 0, 0, 0, tzinfo=timezone.utc)
HANDOFF = 'tmp/_handoff/test-writer--issue-829-phase.yaml'
RECEIPT = b'status: stop\nstop_kind: claude-limit\nstop_reason: |\n  API Error: 429 rate_limit_error\n'


class RunningStallTests(unittest.TestCase):
    def git(self, *args):
        done = subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com', *args],
                              cwd=str(self.repo), text=True, capture_output=True)
        self.assertEqual(done.returncode, 0, done.stderr)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name).resolve() / 'repo'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        (self.repo / 'README.md').write_text('x\n', encoding='utf-8')
        self.git('add', 'README.md')
        self.git('commit', '-qm', 'init')
        self.worktree = '.claude/worktrees/agent-tw01'
        self.git('worktree', 'add', '--detach', '-q', self.worktree, 'HEAD')
        worktree_ledger.open_entry(self.repo, issue=829, agent_type='test-writer', round=1,
                                   branch_name='feature/829', handoff_path=HANDOFF, now=FIXED_NOW)
        self.entry_id = worktree_ledger.bind_agent(self.repo, agent_type='test-writer', agent_id='tw01',
                                                   worktree_path=self.worktree)

    def gitgate(self, *args):
        return subprocess.run(['python3', '-m', 'gitgate', *args], cwd=str(self.repo), text=True,
                              capture_output=True, env={**os.environ, 'PYTHONPATH': str(ROOT)})

    def status(self):
        entry = worktree_ledger.find_by_agent_id(self.repo, 'tw01')
        assert entry is not None
        return entry['status']

    def assert_continuation_rejected(self, reason):
        marker = json.dumps({'entry_id': self.entry_id, 'receipt_sha256': hashlib.sha256(RECEIPT).hexdigest()})
        ack = SimpleNamespace(agent_type='test-writer', issue=829, branch_name='feature/829',
                              expected_oid='a' * 40, repository='owner/repo')
        remote = lambda args, **_kw: subprocess.CompletedProcess(args, 0, 'a' * 40 + '\trefs/heads/feature/829\n', '')
        with self.assertRaisesRegex(IssueStartError, 'CONTINUATION_INVALID.*' + reason):
            validate_author_continuation({'prompt': MARKER + marker}, {'prompt_field': 'prompt'}, ack, self.repo,
                                         remote)

    def test_role_stopped_without_handoff_cannot_be_re_dispatched(self):
        subagent_hooks.run_stop(stdin=io.StringIO(json.dumps({'agent_type': 'test-writer', 'agent_id': 'tw01'})),
                                stdout=io.StringIO(), stderr=io.StringIO(), cwd=self.repo, now=FIXED_NOW,
                                runner=lambda argv, **kw: subprocess.run(argv, **kw))
        self.assertEqual(self.status(), 'running', 'handoff が無い停止は台帳を進めない（#423 の保留）')
        (self.repo / self.worktree / HANDOFF).parent.mkdir(parents=True)
        (self.repo / self.worktree / HANDOFF).write_bytes(RECEIPT)
        collected = self.gitgate('collect-worktree', '--entry', self.entry_id)
        self.assertNotEqual(collected.returncode, 0)
        self.assertIn('WORKTREE_LIVE', collected.stderr)
        self.assert_continuation_rejected('not stopped, collected and released')
        self.assertEqual(self.gitgate('worktree-forget', '--entry', self.entry_id, '--reason', 'limit').returncode, 0)
        released = self.gitgate('worktree-release', self.worktree, '--entry', self.entry_id,
                                '--force-uncollected', '--reason', 'limit')
        self.assertEqual(released.returncode, 0, released.stderr)
        self.assertEqual(self.status(), 'abandoned')
        self.assert_continuation_rejected('not stopped, collected and released')


if __name__ == '__main__':
    unittest.main()
