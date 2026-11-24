import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from finding_triager.github_evidence import github_evidence


class GitHubEvidenceTest(unittest.TestCase):
    def test_exact_github_issue_pr_and_local_diff(self):
        issue = {'number': 783, 'body': 'AC: correct output'}
        repo = {'full_name': 'owner/repo'}
        pr = {'number': 99, 'state': 'open', 'head': {'repo': repo, 'sha': 'a' * 40},
              'base': {'repo': repo, 'sha': 'b' * 40}}
        def run(argv, **kwargs):
            if argv[:3] == ('git', 'remote', 'get-url'):
                out = 'https://github.com/owner/repo.git\n'
            elif argv[:2] == ('git', 'diff'):
                self.assertIn('b' * 40 + '...' + 'a' * 40, argv)
                out = 'diff body'
            else:
                out = json.dumps(issue if '/issues/' in argv[-1] else pr)
            return subprocess.CompletedProcess(argv, 0, stdout=out)
        with tempfile.TemporaryDirectory() as name, patch('finding_triager.github_evidence.subprocess.run', side_effect=run):
            result = github_evidence(Path(name), 783, 99, 'a' * 40)
            self.assertEqual(result['issue_body'], issue['body'])
            self.assertEqual(result['change'], 'diff body')
            pr['head']['sha'] = 'c' * 40
            with self.assertRaisesRegex(ValueError, 'target mismatch'):
                github_evidence(Path(name), 783, 99, 'a' * 40)
            pr['head']['sha'] = 'a' * 40
            issue['number'] = 999
            with self.assertRaisesRegex(ValueError, 'Issue response'):
                github_evidence(Path(name), 783, 99, 'a' * 40)
