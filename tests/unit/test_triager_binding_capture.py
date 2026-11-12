import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codex_worktree_exec.triage_binding_capture import binding_from_capture
from codex_worktree_exec.triage_review_capture import DOMAIN
from finding_triager.adapter import prepare
from codex_worktree_exec.triage_binding_verify import verify_binding_capture, sign_binding


class BindingCaptureTest(unittest.TestCase):
    def test_builds_binding_from_captured_review_and_verified_evidence(self):
        body = b'''### F-783-01
harm: real
harm_detail: data loss
severity: major
scope: in
locus: code.py
summary: failure
evidence: observed
expected: preserved
recheck: run test
'''
        approval = {'issue': 783, 'run_id': 'r', 'target_key': 'k', 'snapshot_oid': 'a' * 40,
                    'input_digest': 'b' * 64, 'source_changes': None, 'approval_context': 'owner-approved', 'triage_phase': 'review',
                    'materials': {'verification_design': {'content': 'VD'},
                                  'solution_planning': {'content': 'CP'}}}
        key = b'k' * 32
        receipt = json.dumps({'schema': 'finding-triage-review-capture/v1', 'producer': 'pr-reviewer', 'source': 'ingested-review', 'phase': 'review', 'round': 1, 'review_sha256': hashlib.sha256(body).hexdigest(),
                              'worktree': '/reviewer', 'review_oid': 'c' * 40, 'approval': approval}).encode()
        mac = hmac.new(key, DOMAIN + receipt, hashlib.sha256).hexdigest()
        github = {'issue_body': 'Issue AC', 'change': 'actual diff'}
        with tempfile.TemporaryDirectory() as name, \
             patch('codex_worktree_exec.triage_binding_capture.github_evidence', return_value=github) as source:
            binding = binding_from_capture(body, receipt, mac, Path(name), key, pr=1, phase='review', round_no=1)
            verify_binding_capture(binding, key)
            altered = dict(binding, reviewer_output='fabricated')
            altered['binding_signature'] = sign_binding({k: v for k, v in altered.items() if k != 'binding_signature'}, key)
            with self.assertRaisesRegex(ValueError, 'capture mismatch'):
                verify_binding_capture(altered, key)
            source.assert_called_once_with(Path(name), 783, 1, 'c' * 40)
            prompt, review = prepare(binding['review'].encode(), binding['review_signature'], key,
                                     binding['expected'], binding['context'].encode(), binding['context_digest'])
            self.assertEqual(review['findings'][0]['finding_id'], 'F-783-01')
            self.assertIn('actual diff', prompt)
            self.assertIn('Issue AC', prompt)
            changed = bytearray(receipt); changed[-2] ^= 1
            with self.assertRaisesRegex(ValueError, 'signature mismatch'):
                binding_from_capture(body, bytes(changed), mac, Path(name), key, pr=1, phase='review', round_no=1)
            with self.assertRaisesRegex(ValueError, 'phase or round mismatch'):
                binding_from_capture(body, receipt, mac, Path(name), key, pr=1, phase='review', round_no=9)

    def test_signed_capture_reaches_triager_and_tamper_cannot_launch(self):
        from codex_worktree_exec.errors import CodexExecError
        from codex_worktree_exec.triager_dispatch import dispatch
        from finding_triager.assessment import FIELDS
        body = b'''### F-783-01
harm: real
harm_detail: data loss
severity: major
scope: in
locus: code.py
summary: failure
evidence: observed
expected: preserved
recheck: run test
'''
        key, capture_key = b'k' * 32, b'x' * 32
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); (root / 'tmp').mkdir()
            reviewer = root / 'reviewer'; reviewer.mkdir()
            approval = {'issue': 783, 'run_id': 'r', 'target_key': 'k', 'snapshot_oid': 'a' * 40,
                        'input_digest': 'b' * 64, 'source_changes': None, 'approval_context': 'owner-approved', 'triage_phase': 'review',
                        'materials': {'verification_design': {'content': 'VD'},
                                      'solution_planning': {'content': 'CP'}}}
            receipt = json.dumps({'schema': 'finding-triage-review-capture/v1', 'producer': 'pr-reviewer', 'source': 'ingested-review', 'phase': 'review', 'round': 1,
                                  'review_sha256': hashlib.sha256(body).hexdigest(),
                                  'worktree': str(reviewer), 'review_oid': 'c' * 40, 'approval': approval}).encode()
            mac = hmac.new(key, DOMAIN + receipt, hashlib.sha256).hexdigest()
            with patch('codex_worktree_exec.triage_binding_capture.github_evidence', return_value={'issue_body': 'AC', 'change': 'diff'}):
                binding = binding_from_capture(body, receipt, mac, root, key, pr=1, phase='review', round_no=1)
            binding_path = root / 'tmp/binding.json'
            binding_path.write_text(json.dumps(binding))
            req = SimpleNamespace(binding_file=Path('tmp/binding.json'), output_file=Path('tmp/out.json'),
                                  role='finding-triager', model='model', reasoning_effort='high', timeout_seconds=30)
            env = {'TRIAGER_REVIEW_KEY': key.hex(), 'TRIAGER_CAPTURE_KEY': capture_key.hex()}
            facts = dict.fromkeys(FIELDS, False)
            assessments = [{'finding_id': 'F-783-01', 'harm': 'real', 'scope': 'in',
                            'evidence': dict.fromkeys(('ac', 'vd_cp', 'design', 'change'), 'reason'), 'facts': facts}]
            def git(argv, **kwargs):
                text = 'worktree ' + str(reviewer) + '\n' if 'worktree' in argv else 'c' * 40
                return SimpleNamespace(stdout=text)
            def run(argv, prompt, **kwargs):
                Path(argv[argv.index('--output-last-message') + 1]).write_text(json.dumps(assessments))
                return 0
            with patch('codex_worktree_exec.triager_dispatch.verify_source_snapshot'), \
                 patch('codex_worktree_exec.triager_dispatch.subprocess.run', side_effect=git), \
                 patch('codex_worktree_exec.triager_dispatch.run_codex', side_effect=run) as launch:
                self.assertEqual(dispatch(req, root, root, env, 'codex'), 0)
                launch.assert_called_once()
                self.assertTrue((root / req.output_file).exists())
                binding['reviewer_output'] += 'tampered'
                binding_path.write_text(json.dumps(binding))
                launch.reset_mock()
                with self.assertRaises(CodexExecError):
                    dispatch(req, root, root, env, 'codex')
                launch.assert_not_called()
