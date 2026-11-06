"""Publish trusted verification job results to their tested commit."""
import json
import os
import re
import urllib.request


def publish(environ):
    oid = environ['HEAD_OID']
    if not re.fullmatch(r'[0-9a-f]{40}', oid):
        raise ValueError('invalid head OID')
    repository = environ['REPOSITORY']
    run_url = f"{environ['SERVER_URL']}/{repository}/actions/runs/{environ['RUN_ID']}"
    conclusions = {}
    for name in ('unittest', 'typecheck'):
        conclusion = 'success' if environ[f'{name.upper()}_RESULT'] == 'success' else 'failure'
        payload = {
            'name': name, 'head_sha': oid, 'status': 'completed',
            'conclusion': conclusion, 'details_url': run_url,
            'output': {'title': f'Conflict repair {name}',
                       'summary': f'{name} verification on the repaired commit.'},
        }
        request = urllib.request.Request(
            f"{environ['API_URL']}/repos/{repository}/check-runs",
            data=json.dumps(payload).encode(), headers={
                'Authorization': f"Bearer {environ['GH_TOKEN']}",
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
            }, method='POST')
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        if (result.get('head_sha') != oid or result.get('conclusion') != conclusion
                or result.get('name') != name):
            raise ValueError('check API response did not match the requested name, OID and result')
        conclusions[name] = conclusion
    return conclusions


def main():
    conclusions = publish(os.environ)
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
        summary.write(f"Verification checks published for {os.environ['HEAD_OID']}: "
                      f"{conclusions}. Ruleset satisfaction requires live confirmation.\n")


if __name__ == '__main__':
    main()
