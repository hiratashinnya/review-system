"""旧policy PRと導入済defaultを持つ実Git fixture。"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from issue_start import worktree_ledger
from issue_start.gate_dispatch import parse_dispatch_payload
from issue_start.pr_rereview import MARKER


class LegacyPrFixture:
    def __init__(self, directory):
        self.root, self.remote = Path(directory) / 'repo', Path(directory) / 'remote.git'
        self.root.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'Test')
        self.manifest = self.root / 'issue_start/managed-entrypoints-v2.json'
        self.manifest.parent.mkdir()
        self.manifest.write_text(json.dumps({'policy_version':'issue-start/1.0'}))
        self.commit('old policy', '2026-10-01T00:00:00Z')
        self.old = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-qb', 'feature/legacy')
        (self.root / 'source.py').write_text('fixed = True\n')
        self.commit('legacy fix', '2026-10-18T00:00:00Z')
        self.oid = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-q', 'main')
        self.manifest.write_text(json.dumps({'policy_version':'issue-start/2.0'}))
        self.commit('policy rollout', '2026-10-20T00:00:00Z')
        self.rollout = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-q', 'feature/legacy')
        self.git('clone', '-q', '--bare', str(self.root), str(self.remote))
        self.git('remote', 'add', 'origin', 'https://github.com/owner/repo.git')
        now = datetime.now(timezone.utc)
        self.entry = worktree_ledger.open_entry(self.root, issue=371, agent_type='issue-fixer',
                     round=3, branch_name='feature/legacy', handoff_path='tmp/_handoff/issue-fixer--issue-371.yaml', now=now)
        self.receipt = self.root / 'tmp/_handoff/collected/fixer.yaml'
        self.receipt.parent.mkdir(parents=True)
        self.receipt.write_text('status: fixed\n')
        for status in ('running', 'stopped', 'collected', 'released'):
            worktree_ledger.mark(self.root, self.entry, status, now=now,
                                collected_to='tmp/_handoff/collected/fixer.yaml')
        self.raw = dict(repository='owner/repo', issue=371, pr=627, branch_name='feature/legacy',
                        expected_oid=self.oid, fixer_entry_id=self.entry,
                        receipt_sha256=hashlib.sha256(self.receipt.read_bytes()).hexdigest())
        self.pr = dict(number=627, state='open', merged=False, created_at='2026-10-18T00:00:00Z',
                       head=dict(repo=dict(full_name='owner/repo'), ref='feature/legacy', sha=self.oid),
                       base=dict(repo=dict(full_name='owner/repo')))

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, text=True,
                              capture_output=True, check=True).stdout.strip()

    def commit(self, message, date='2026-10-18T00:00:00Z'):
        self.git('add', '-A')
        env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(['git','commit','-qm',message], cwd=self.root, env=env, check=True)

    def runner(self, argv, **kwargs):
        if argv[:2] == ['gh','api']:
            value = self.pr if '/pulls/' in argv[2] else dict(default_branch='main')
            return subprocess.CompletedProcess(argv, 0, json.dumps(value), '')
        return subprocess.run([str(self.remote) if item == 'https://github.com/owner/repo.git'
                               else item for item in argv], **kwargs)

    def parse(self, *, role='pr-reviewer', extra='', runner=None):
        prompt = MARKER + json.dumps(self.raw) + extra
        return parse_dispatch_payload(dict(tool_name='Agent', tool_input=dict(
            subagent_type=role, prompt=prompt)), cwd=self.root, runner=runner or self.runner)

    def change_ledger(self, **changes):
        worktree_ledger.update_ledger(self.root, lambda doc: doc['entries'][-1].update(changes))

    def hook(self):
        import io
        from functools import partial
        from unittest.mock import patch
        from issue_start.hook import run
        payload = dict(tool_name='Agent', tool_input=dict(subagent_type='pr-reviewer',
                       prompt=MARKER + json.dumps(self.raw)))
        output, evidence = io.StringIO(), io.StringIO()
        parser = partial(parse_dispatch_payload, runner=self.runner)
        with patch('issue_start.hook.parse_dispatch_payload', new=parser):
            result = run(stdin=io.StringIO(json.dumps(payload)), stdout=output,
                         stderr=evidence, cwd=self.root, ledger_root=self.root)
        return result, output.getvalue(), evidence.getvalue()
