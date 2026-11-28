import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codex_worktree_exec.triage_binding_capture import binding_from_capture
from codex_worktree_exec.triage_review_capture import capture_existing
from codex_worktree_exec.triager_dispatch import validate_binding


class RealSnapshotTest(unittest.TestCase):
    def test_distinct_source_snapshot_and_review_head_with_approved_change(self):
        body = b'''### F-783-01
harm: real
harm_detail: data loss
severity: major
scope: in
locus: code.py
summary: issue
evidence: observed
expected: retained
recheck: run
'''
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / 'repo'; root.mkdir()
            def git(*args):
                return subprocess.run(['git', '-C', str(root), *args], check=True,
                                      capture_output=True, text=True).stdout.strip()
            git('init', '-q'); git('config', 'user.email', 'test@example.com'); git('config', 'user.name', 'test')
            (root / '.gitignore').write_text('tmp/\n'); (root / 'code.py').write_text('before\n')
            git('add', '.'); git('commit', '-qm', 'source snapshot'); snapshot = git('rev-parse', 'HEAD')
            (root / 'code.py').write_text('after\n'); git('add', 'code.py'); git('commit', '-qm', 'implementation')
            head = git('rev-parse', 'HEAD'); reviewer = Path(name) / 'reviewer'
            git('worktree', 'add', '--detach', str(reviewer), head); (root / 'tmp').mkdir()
            digest = hashlib.sha256((root / 'code.py').read_bytes()).hexdigest()
            approval = {'issue': 783, 'run_id': 'r', 'target_key': 'k', 'snapshot_oid': snapshot,
                        'input_digest': 'b' * 64, 'source_changes': {'code.py': digest},
                        'approval_context': 'approved', 'triage_phase': 'review', 'materials': {
                            'verification_design': {'content': 'VD'}, 'solution_planning': {'content': 'CP'}}}
            key, capture_key = b'k' * 32, b'x' * 32
            captured = capture_existing(body, reviewer, approval, head, key, 'review', 1)
            with patch('codex_worktree_exec.triage_binding_capture.github_evidence',
                       return_value={'issue_body': 'AC', 'change': 'diff'}):
                binding = binding_from_capture(*captured, root, key, pr=1, phase='review', round_no=1)
            path = root / 'tmp/binding.json'; path.write_text(json.dumps(binding))
            req = SimpleNamespace(binding_file=Path('tmp/binding.json'))
            env = {'TRIAGER_REVIEW_KEY': key.hex(), 'TRIAGER_CAPTURE_KEY': capture_key.hex()}
            self.assertNotEqual(snapshot, head)
            validate_binding(req, root, root, env)
            (root / 'code.py').write_text('tampered\n')
            with self.assertRaises(ValueError): validate_binding(req, root, root, env)
