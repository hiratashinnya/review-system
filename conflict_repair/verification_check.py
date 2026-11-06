"""Publish the trusted verification job result to its tested commit."""
import json
import os
import re
import urllib.request


def publish(environ):
    oid = environ['HEAD_OID']
    if not re.fullmatch(r'[0-9a-f]{40}', oid):
        raise ValueError('invalid head OID')
    conclusion = 'success' if environ['VERIFY_RESULT'] == 'success' else 'failure'
    repository = environ['REPOSITORY']
    run_url = f"{environ['SERVER_URL']}/{repository}/actions/runs/{environ['RUN_ID']}"
    payload = {
        'name': 'conflict-repair-verification', 'head_sha': oid,
        'status': 'completed', 'conclusion': conclusion, 'details_url': run_url,
        'output': {'title': 'Conflict repair verification',
                   'summary': 'unittest and guidance_sync; required checks are not assessed.'},
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
    if result.get('head_sha') != oid or result.get('conclusion') != conclusion:
        raise ValueError('check API response did not match the requested OID and result')
    return conclusion


def main():
    conclusion = publish(os.environ)
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
        summary.write(f"Verification check published for {os.environ['HEAD_OID']} "
                      f"({conclusion}). Required checks remain unconfirmed.\n")


if __name__ == '__main__':
    main()
