"""Regression tests for the separate verification check publisher."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from conflict_repair.verification_check import publish


class VerificationCheckTests(unittest.TestCase):
    def setUp(self):
        self.oid = 'a' * 40
        self.env = {'HEAD_OID': self.oid, 'VERIFY_RESULT': 'success',
                    'REPOSITORY': 'owner/repo', 'SERVER_URL': 'https://github.com',
                    'RUN_ID': '123', 'API_URL': 'https://api.github.com',
                    'GH_TOKEN': 'test-token'}

    def response(self, oid=None, conclusion='success'):
        return io.BytesIO(json.dumps({'head_sha': oid or self.oid,
                                    'conclusion': conclusion}).encode())

    @patch('conflict_repair.verification_check.urllib.request.urlopen')
    def test_success_posts_to_tested_oid(self, urlopen):
        urlopen.return_value = self.response()
        self.assertEqual(publish(self.env), 'success')
        request = urlopen.call_args.args[0]
        data = json.loads(request.data)
        self.assertEqual(data['head_sha'], self.oid)
        self.assertEqual(data['conclusion'], 'success')
        self.assertIn('required checks are not assessed', data['output']['summary'])
        self.assertEqual(request.full_url, 'https://api.github.com/repos/owner/repo/check-runs')

    @patch('conflict_repair.verification_check.urllib.request.urlopen')
    def test_non_success_never_reports_success(self, urlopen):
        for status in ('failure', 'cancelled', 'skipped', 'unknown'):
            with self.subTest(status=status):
                self.env['VERIFY_RESULT'] = status
                urlopen.return_value = self.response(conclusion='failure')
                self.assertEqual(publish(self.env), 'failure')
                self.assertEqual(json.loads(urlopen.call_args.args[0].data)['conclusion'], 'failure')

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
        for oid, conclusion in (('b' * 40, 'success'), (self.oid, 'failure')):
            with self.subTest(oid=oid, conclusion=conclusion):
                urlopen.return_value = self.response(oid, conclusion)
                with self.assertRaises(ValueError):
                    publish(self.env)
