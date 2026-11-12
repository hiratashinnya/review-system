import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codex_worktree_exec.triage_review_capture import DOMAIN, capture_reviewer


class ReviewerCaptureTest(unittest.TestCase):
    def test_receipt_covers_actual_output_and_detects_changes_in_approval(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); (root / 'tmp').mkdir()
            req = SimpleNamespace(role='pr-reviewer', worktree=root, binding_file=Path('tmp/binding.json'),
                                  prompt_file=Path('tmp/prompt'), timeout_seconds=30)
            marker = {'binding_file': 'tmp/binding.json', 'approval_file': 'tmp/approval.json'}
            material = {'issue': 783, 'materials': {'solution_planning': {'sha256': 'a' * 64}}}
            key = b'k' * 32
            def run(argv, prompt, **kwargs):
                self.assertNotIn('secret', kwargs['environ'])
                Path(argv[0]).write_text('review output')
                return 0
            with patch('codex_worktree_exec.triage_review_capture.refuse_nested_launch'), \
                 patch('codex_worktree_exec.triage_review_capture.bind_worktree', return_value=root), \
                 patch('codex_worktree_exec.triage_review_capture.verify_profile_pinned'), \
                 patch('codex_worktree_exec.triage_review_capture.verify_project_trusted'), \
                 patch('codex_worktree_exec.triage_review_capture.codex_home'), \
                 patch('codex_worktree_exec.triage_review_capture.approved_materials', return_value=material) as approved, \
                 patch('codex_worktree_exec.triage_review_capture.read_prompt', return_value='prompt'), \
                 patch('codex_worktree_exec.triage_review_capture.compose_prompt', return_value='prompt'), \
                 patch('codex_worktree_exec.triage_review_capture.build_codex_argv', side_effect=lambda r, w, o, c: [str(o)]), \
                 patch('codex_worktree_exec.triage_review_capture.run_codex', side_effect=run):
                body, raw, mac = capture_reviewer(req, root, marker, {}, 'codex', key)
                self.assertEqual(json.loads(raw)['review_sha256'], hashlib.sha256(body).hexdigest())
                self.assertEqual(mac, hmac.new(key, DOMAIN + raw, hashlib.sha256).hexdigest())
                self.assertEqual(approved.call_count, 2)
                approved.side_effect = [material, {**material, 'issue': 999}]
                with self.assertRaisesRegex(ValueError, 'changed during'):
                    capture_reviewer(req, root, marker, {}, 'codex', key)
            self.assertEqual(list((root / 'tmp').iterdir()), [])
