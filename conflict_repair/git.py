"""隔離された一時 Git repository を操作する。"""
import base64
import os
import subprocess
import tempfile
from pathlib import Path

from guidance_sync.sources import COMMON_SOURCE, PRINCIPLES_SOURCE, TARGETS


def run(repo, *args, check=True, extra_env=None):
    env = os.environ.copy()
    env.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                'GIT_TERMINAL_PROMPT': '0'})
    if extra_env:
        env.update(extra_env)
    if os.environ.get('GH_TOKEN'):
        auth = base64.b64encode(f"x-access-token:{os.environ['GH_TOKEN']}".encode()).decode()
        env.update({'GIT_CONFIG_COUNT': '2', 'GIT_CONFIG_KEY_0': 'http.https://github.com/.extraheader',
                    'GIT_CONFIG_VALUE_0': '', 'GIT_CONFIG_KEY_1': 'http.https://github.com/.extraheader',
                    'GIT_CONFIG_VALUE_1': f'Authorization: basic {auth}'})
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args],
                            cwd=repo, env=env, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(f"git {args[0]}: {result.stderr.strip()}")
    return result


def prepare(source, repo, base, head):
    run(source, 'fetch', '--no-tags', 'origin', base, head)
    run(source, 'clone', '--no-local', '--no-checkout', str(source), str(repo))
    run(repo, 'fetch', str(source), base, head)
    run(repo, 'config', 'user.name', 'github-actions[bot]')
    run(repo, 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    run(repo, 'checkout', '--detach', head)
    (repo / '.git' / 'info' / 'attributes').write_text('* !merge\n')
    return run(repo, 'merge', '--no-ff', '--no-commit', base, check=False)


def conflicts(repo):
    output = run(repo, 'diff', '--name-only', '--diff-filter=U', '-z').stdout
    return set(filter(None, output.split('\0')))


def commit(repo):
    run(repo, 'add', '--', 'AGENTS.md', '.github/copilot-instructions.md')
    for path in {COMMON_SOURCE, PRINCIPLES_SOURCE, *TARGETS.values(), *TARGETS}:
        working = run(repo, 'hash-object', '--no-filters', '--', path).stdout.strip()
        staged = run(repo, 'rev-parse', f':{path}').stdout.strip()
        if working != staged:
            raise ValueError(f'stage 後の内容が作業ファイルと不一致: {path}')
    run(repo, 'commit', '--no-verify', '-m', 'Merge default branch and regenerate guidance')
    return run(repo, 'rev-parse', 'HEAD').stdout.strip()


def push(source, repo, branch, expected_oid):
    url = run(source, 'remote', 'get-url', 'origin').stdout.strip()
    with tempfile.TemporaryDirectory(prefix='trusted-push-hook-') as temp:
        hook = Path(temp) / 'pre-push'
        hook.write_text("""#!/bin/sh
count=0
while read -r local_ref local_oid remote_ref remote_oid; do
    count=$((count + 1))
    [ "$remote_ref" = "$REPAIR_REF" ] && [ "$remote_oid" = "$REPAIR_EXPECTED_OID" ] || exit 1
done
[ "$count" -eq 1 ]
""")
        hook.chmod(0o700)
        run(repo, '-c', f'core.hooksPath={temp}', 'push', url, f'HEAD:refs/heads/{branch}',
            extra_env={'REPAIR_REF': f'refs/heads/{branch}', 'REPAIR_EXPECTED_OID': expected_oid})
