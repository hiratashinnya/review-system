"""Resolve and revalidate a PR's live test merge using trusted code."""
import json
import os
import re
import time
from pathlib import Path

from . import git
from .github import GitHub


def live_pr(api, number, head_oid):
    default = api.default_branch()
    pr = api.request(f'/pulls/{number}')
    base, head = pr['base'], pr['head']
    if (pr['number'] != int(number) or pr['state'] != 'open'
            or base['repo']['full_name'] != api.repository or head['repo']['full_name'] != api.repository
            or base['ref'] != default or head['ref'] == default or head['sha'] != head_oid):
        raise ValueError('PR is not an eligible live merge target')
    base_oid = api.branch_oid(default)
    if api.branch_oid(head['ref']) != head_oid:
        raise ValueError('head branch changed')
    return pr, default, base_oid


def resolve(api, number, head_oid, source):
    if not re.fullmatch(r'[1-9][0-9]*', number) or not re.fullmatch(r'[0-9a-f]{40}', head_oid):
        raise ValueError('invalid PR number or head OID')
    initial = None
    for attempt in range(6):
        pr, default, base_oid = live_pr(api, number, head_oid)
        snapshot = (default, base_oid, pr['head']['ref'])
        if initial is not None and snapshot != initial:
            raise ValueError('PR or base branch changed while waiting for test merge')
        initial = snapshot
        if pr['mergeable'] is not None:
            break
        if attempt < 5:
            time.sleep(5)
    if pr['mergeable'] is not True:
        raise ValueError('PR is not an eligible live merge target')
    head = pr['head']
    merge_oid = pr['merge_commit_sha']
    if not isinstance(merge_oid, str) or not re.fullmatch(r'[0-9a-f]{40}', merge_oid):
        raise ValueError('merge commit unavailable')
    git.run(source, 'fetch', '--no-tags', 'origin', f'refs/pull/{number}/merge')
    parents = git.run(source, 'rev-list', '--parents', '-n', '1', 'FETCH_HEAD').stdout.split()
    if parents != [merge_oid, base_oid, head_oid]:
        raise ValueError('test merge or its parents changed')
    return {'number': number, 'base_ref': default, 'base_oid': base_oid,
            'head_ref': head['ref'], 'head_oid': head_oid, 'merge_oid': merge_oid}


def main():
    env = os.environ
    current = resolve(GitHub(env['REPOSITORY']), env['PR_NUMBER'], env['HEAD_OID'], Path.cwd())
    if current['base_oid'] != env['TRUSTED_SHA']:
        raise ValueError('default branch changed since workflow dispatch')
    if env.get('EXPECTED_TARGET'):
        if current != json.loads(env['EXPECTED_TARGET']):
            raise ValueError('PR or test merge changed after verification')
        return
    with open(env['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write('target=' + json.dumps(current, separators=(',', ':')) + '\n')
        output.write('oids=' + json.dumps([current['head_oid'], current['merge_oid']]) + '\n')


if __name__ == '__main__':
    main()
