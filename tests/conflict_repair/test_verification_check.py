"""Regression tests for verification check publishing and job parity."""
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from conflict_repair.verification_check import publish


class VerificationCheckTests(unittest.TestCase):
    def setUp(self):
        self.oid = 'a' * 40
        self.env = {'HEAD_OID': self.oid, 'UNITTEST_RESULT': 'success',
                    'TYPECHECK_RESULT': 'success', 'REPOSITORY': 'owner/repo',
                    'SERVER_URL': 'https://github.com', 'RUN_ID': '123',
                    'API_URL': 'https://api.github.com', 'GH_TOKEN': 'test-token'}

    def response(self, name, oid=None, conclusion='success'):
        return io.BytesIO(json.dumps({'name': name, 'head_sha': oid or self.oid,
                                     'conclusion': conclusion}).encode())

    @patch('conflict_repair.verification_check.urllib.request.urlopen')
    def test_success_posts_each_required_check_to_tested_oid(self, urlopen):
        urlopen.side_effect = [self.response('unittest'), self.response('typecheck')]
        self.assertEqual(publish(self.env), {'unittest': 'success', 'typecheck': 'success'})
        for call, name in zip(urlopen.call_args_list, ('unittest', 'typecheck')):
            request = call.args[0]
            data = json.loads(request.data)
            self.assertEqual((data['name'], data['head_sha'], data['conclusion']),
                             (name, self.oid, 'success'))
            self.assertEqual(request.full_url, 'https://api.github.com/repos/owner/repo/check-runs')

    @patch('conflict_repair.verification_check.urllib.request.urlopen')
    def test_non_success_never_reports_success(self, urlopen):
        for status in ('failure', 'cancelled', 'skipped', 'unknown'):
            with self.subTest(status=status):
                self.env['UNITTEST_RESULT'] = status
                urlopen.side_effect = [self.response('unittest', conclusion='failure'),
                                       self.response('typecheck')]
                self.assertEqual(publish(self.env), {'unittest': 'failure', 'typecheck': 'success'})
                self.assertEqual(json.loads(urlopen.call_args_list[-2].args[0].data)['conclusion'], 'failure')

    @patch('conflict_repair.verification_check.urllib.request.urlopen')
    def test_typecheck_failure_is_independent(self, urlopen):
        self.env['TYPECHECK_RESULT'] = 'cancelled'
        urlopen.side_effect = [self.response('unittest'),
                               self.response('typecheck', conclusion='failure')]
        self.assertEqual(publish(self.env), {'unittest': 'success', 'typecheck': 'failure'})

    @patch('conflict_repair.verification_check.urllib.request.urlopen')
    def test_invalid_oid_never_posts(self, urlopen):
        self.env['HEAD_OID'] = 'not-an-oid'
        with self.assertRaises(ValueError):
            publish(self.env)
        urlopen.assert_not_called()

    @patch('conflict_repair.verification_check.urllib.request.urlopen')
    def test_api_error_propagates(self, urlopen):
        urlopen.side_effect = HTTPError('https://api.github.com', 403, 'forbidden', {}, None)
        with self.assertRaises(HTTPError):
            publish(self.env)

    @patch('conflict_repair.verification_check.urllib.request.urlopen')
    def test_mismatched_response_fails(self, urlopen):
        for name, oid, conclusion in (('unittest', 'b' * 40, 'success'),
                                      ('unittest', self.oid, 'failure'),
                                      ('wrong', self.oid, 'success')):
            with self.subTest(name=name, oid=oid, conclusion=conclusion):
                urlopen.side_effect = [self.response(name, oid, conclusion)]
                with self.assertRaises(ValueError):
                    publish(self.env)

    def test_verification_commands_match_pr_jobs(self):
        tests = Path('.github/workflows/tests.yml').read_text()
        verify = Path('.github/workflows/conflict-repair-verify.yml').read_text()
        for name, next_job in (('unittest', 'typecheck'), ('typecheck', 'feedback-ledger')):
            source = tests.split(f'  {name}:\n', 1)[1].split(f'  {next_job}:\n', 1)[0]
            end = 'verify-typecheck' if name == 'unittest' else 'report'
            target = verify.split(f'  verify-{name}:\n', 1)[1].split(f'  {end}:\n', 1)[0]
            if name == 'unittest':
                target = target.split('      - name: Guidance sync check', 1)[0]
            marker = '      - name: Set up Python'
            self.assertEqual(source[source.index(marker):].strip(),
                             target[target.index(marker):].strip())
