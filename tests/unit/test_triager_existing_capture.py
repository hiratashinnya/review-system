import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from issue_start.triage_existing_capture import execute_with_capture
from codex_worktree_exec.triage_binding_verify import verify_binding_capture


class ExistingCaptureTest(unittest.TestCase):
    def test_normal_review_is_captured_once_and_binds_exact_bytes(self):
        body = b'''### F-783-42
harm: real
harm_detail: data loss
severity: major
scope: in
locus: code.py
summary: unique finding
evidence: observed
expected: preserved
recheck: run test
'''
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); (root / 'tmp').mkdir()
            req = SimpleNamespace(role='pr-reviewer', output_file=Path('tmp/review.md'))
            approval = {'issue': 783, 'run_id': 'r', 'target_key': 'k', 'snapshot_oid': 'a' * 40,
                        'input_digest': 'b' * 64, 'source_changes': {}, 'approval_context': 'approved',
                        'materials': {'verification_design': {'content': 'VD'},
                                      'solution_planning': {'content': 'CP'}}}
            calls = []
            def execute(args, cwd):
                calls.append(args); (cwd / req.output_file).write_bytes(body); return 0
            with patch('issue_start.triage_existing_capture.approved_materials', return_value=approval), \
                 patch('issue_start.triage_existing_capture._head', return_value='c' * 40), \
                 patch('codex_worktree_exec.triage_binding_capture.github_evidence',
                       return_value={'issue_body': 'AC', 'change': 'diff'}) as github:
                result = execute_with_capture(req, ['review'], root, {}, b'k' * 32, 3,
                                              'review', 2, 'tmp/triage.json', execute)
            self.assertEqual(result, 0); self.assertEqual(calls, [['review']])
            binding = json.loads((root / 'tmp/triage.json').read_text())
            receipt = verify_binding_capture(binding, b'k' * 32)
            self.assertEqual(receipt['review_sha256'], hashlib.sha256(body).hexdigest())
            self.assertEqual(json.loads(binding['review'])['findings'][0]['finding_id'], 'F-783-42')
            self.assertEqual(binding['expected']['review_oid'], 'c' * 40)
            github.assert_called_once_with(root, 783, 3, 'c' * 40)
            binding['reviewer_output'] += 'different'
            with self.assertRaises(ValueError): verify_binding_capture(binding, b'k' * 32)

    def test_changed_approval_prevents_capture(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); (root / 'tmp').mkdir()
            req = SimpleNamespace(role='pr-reviewer', output_file=Path('tmp/review.md'))
            def execute(args, cwd):
                (cwd / req.output_file).write_text('review'); return 0
            with patch('issue_start.triage_existing_capture.approved_materials', side_effect=[{'a': 1}, {'a': 2}]), \
                 patch('issue_start.triage_existing_capture._head', return_value='c' * 40):
                with self.assertRaisesRegex(ValueError, 'changed'):
                    execute_with_capture(req, [], root, {}, b'k' * 32, 3, 'review', 1, 'tmp/triage.json', execute)
            self.assertFalse((root / 'tmp/triage.json').exists())

    def test_readonly_entrypoint_passes_existing_reviewer_to_capture(self):
        from issue_start.readonly_workspace import main
        request = SimpleNamespace(role='pr-reviewer', worktree=Path('/target'),
                                  binding_file=Path('tmp/binding.json'), prompt_file=Path('tmp/prompt.md'))
        args = ['--source', '/source', '--approval-file', 'tmp/approval.json',
                '--triage-pr', '3', '--triage-phase', 'review', '--triage-round', '2',
                '--triage-output', 'tmp/triage.json', '--role', 'pr-reviewer']
        with patch('issue_start.readonly_workspace.parse_request', return_value=request), \
             patch('issue_start.readonly_workspace.prepare_readonly_workspace', return_value=Path('/target')), \
             patch('issue_start.triage_existing_capture.execute_with_capture', return_value=0) as capture, \
             patch.dict('os.environ', {'TRIAGER_REVIEW_KEY': (b'k' * 32).hex()}):
            self.assertEqual(main(args), 0)
        self.assertIs(capture.call_args.args[0], request)
        self.assertEqual(capture.call_args.args[5:9], (3, 'review', 2, 'tmp/triage.json'))
