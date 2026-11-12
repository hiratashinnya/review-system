import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from codex_worktree_exec.errors import CodexExecError
from codex_worktree_exec.child_environment import build_codex_child_environment
from codex_worktree_exec.invocation import build_codex_argv
from codex_worktree_exec.triager_dispatch import dispatch
from codex_worktree_exec.triager_profile import verify_readonly_profile
from finding_triager.assessment import FIELDS
from finding_triager.validator import validate_proposal


class TriagerDispatchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); (self.root / 'tmp').mkdir()
        self.reviewer = self.root / 'reviewer'; self.reviewer.mkdir()
        self.review_key = b'x' * 32; self.capture_key = b'y' * 32
        self.expected = {'issue': 783, 'phase': 'review', 'round': 1, 'run_id': 'r1',
                         'target_key': 'target', 'input_digest': 'a' * 64, 'snapshot_oid': 'b' * 40}
        review = {**self.expected, 'producer': 'pr-reviewer', 'findings': [
            {'finding_id': 'F-1', 'harm': 'real', 'scope': 'in', 'severity': 'major',
             'harm_detail': 'loss', 'evidence': 'evidence'}]}
        self.raw = json.dumps(review).encode()
        self.context = json.dumps(dict.fromkeys(('ac', 'vd_cp', 'design', 'change'), 'evidence')).encode()
        self.digest = hashlib.sha256(self.context).hexdigest()
        self.binding = {'review': self.raw.decode(), 'review_signature': hmac.new(
            self.review_key, self.raw, hashlib.sha256).hexdigest(), 'expected': self.expected,
            'context': self.context.decode(), 'context_digest': self.digest,
            'reviewer_worktree': str(self.reviewer)}
        self.req = SimpleNamespace(binding_file=Path('tmp/binding.json'), output_file=Path('tmp/out.json'),
                                   role='finding-triager', model='model', reasoning_effort='high', timeout_seconds=30)
        self.env = {'TRIAGER_REVIEW_KEY': self.review_key.hex(), 'TRIAGER_CAPTURE_KEY': self.capture_key.hex()}
        self.facts = dict.fromkeys(FIELDS, False)
        self.assessments = [{'finding_id': 'F-1', 'harm': 'real', 'scope': 'in',
                             'evidence': dict.fromkeys(('ac', 'vd_cp', 'design', 'change'), 'evidence'),
                             'facts': self.facts}]

    def write_binding(self):
        (self.root / 'tmp/binding.json').write_text(json.dumps(self.binding))

    def launch(self, fail=False):
        self.write_binding()
        def run(argv, prompt, **kwargs):
            self.assertIn('harm_detail に書くのは実害だけ', prompt)
            self.assertIn('default_permissions="adviser"', argv)
            Path(argv[argv.index('--output-last-message') + 1]).write_text(json.dumps(self.assessments))
            return 2 if fail else 0
        def git(argv, **kwargs):
            stdout = ("worktree " + str(self.reviewer) + "\n") if "worktree" in argv else "b" * 40
            return SimpleNamespace(stdout=stdout)
        with patch('codex_worktree_exec.triager_dispatch.verify_source_snapshot'), \
             patch('codex_worktree_exec.triager_dispatch.subprocess.run', side_effect=git), \
             patch('codex_worktree_exec.triager_dispatch.run_codex', side_effect=run) as execute:
            result = dispatch(self.req, self.root, self.root, self.env, 'codex')
        return result, execute

    def test_host_captures_and_authenticates_output(self):
        result, execute = self.launch(); self.assertEqual(result, 0); execute.assert_called_once()
        out = json.loads((self.root / self.req.output_file).read_text())
        self.assertEqual(validate_proposal(out['artifact'], self.raw, self.binding['review_signature'],
                         self.review_key, self.expected, self.context, self.digest,
                         out['capture'].encode(), out['signature'], self.capture_key), out['artifact'])
        self.assertEqual(list((self.root / 'tmp').glob('.triager-*')), [])

    def test_rejects_same_context_and_bad_digest_before_launch(self):
        for field, value in [('reviewer_worktree', str(self.root)), ('context_digest', '0' * 64)]:
            original = self.binding[field]; self.binding[field] = value
            with self.subTest(field=field), self.assertRaises(CodexExecError):
                self.launch()
            self.binding[field] = original
        self.assertFalse((self.root / self.req.output_file).exists())

    def test_failure_does_not_produce_capture(self):
        with self.assertRaises(CodexExecError): self.launch(fail=True)
        self.assertFalse((self.root / self.req.output_file).exists())
        self.assertEqual(list((self.root / 'tmp').glob('.triager-*')), [])

    def test_child_environment_excludes_trusted_keys(self):
        child = build_codex_child_environment(self.env)
        self.assertNotIn("TRIAGER_REVIEW_KEY", child)
        self.assertNotIn("TRIAGER_CAPTURE_KEY", child)

    def test_profile_rejects_writable_and_network(self):
        config = self.root / '.codex'; config.mkdir()
        base = '[permissions.adviser]\nextends=":read-only"\n[permissions.adviser.network]\nenabled=false\nallow_local_binding=false\ndangerously_allow_all_unix_sockets=false\ndangerously_allow_non_loopback_proxy=false\n[permissions.adviser.filesystem]\n"~/.codex/auth.json"="deny"\n"~/.config/gh"="deny"\n"~/.claude/.credentials.json"="deny"\n"~/.ssh"="deny"\n'
        for text in (base.replace(':read-only', ':workspace'), base.replace('enabled=false', 'enabled=true')):
            (config / 'config.toml').write_text(text)
            with self.assertRaises(ValueError): verify_readonly_profile(self.root)
        (config / 'config.toml').write_text(base); verify_readonly_profile(self.root)
