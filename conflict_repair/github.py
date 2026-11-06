"""GitHub の live PR と branch 情報を取得する。"""
import json
import os
import urllib.parse
import urllib.request


class GitHub:
    def __init__(self, repository):
        self.repository = repository
        self.root = f"https://api.github.com/repos/{repository}"
        self.token = os.environ['GH_TOKEN']

    def request(self, path, data=None):
        payload = None if data is None else json.dumps(data).encode()
        request = urllib.request.Request(self.root + path, data=payload, headers={
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        })
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
            return json.loads(content) if content else None

    def default_branch(self):
        return self.request('')['default_branch']

    def pulls(self):
        result = []
        for page in range(1, 10001):
            items = self.request(f'/pulls?state=open&per_page=100&page={page}')
            if not isinstance(items, list):
                raise ValueError('invalid pull list')
            result.extend(items)
            if len(items) < 100:
                return result
        raise ValueError('pull pagination limit exceeded')

    def branch_oid(self, branch):
        encoded = urllib.parse.quote(branch, safe='')
        return self.request(f'/branches/{encoded}')['commit']['sha']

    def dispatch(self, workflow, ref, oid, number):
        self.request(f'/actions/workflows/{workflow}/dispatches',
                     {'ref': ref, 'inputs': {'head_oid': oid, 'pr_number': str(number)}})
