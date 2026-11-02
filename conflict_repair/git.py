"""隔離された一時 Git repository を操作する。"""
import base64
import os
import subprocess
from pathlib import Path


def run(repo, *args, check=True):
    env = os.environ.copy()
    env.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                'GIT_TERMINAL_PROMPT': '0'})
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
    return run(repo, 'merge', '--no-ff', '--no-commit', base, check=False)


def conflicts(repo):
    output = run(repo, 'diff', '--name-only', '--diff-filter=U', '-z').stdout
    return set(filter(None, output.split('\0')))


def commit(repo):
    run(repo, 'add', '--', 'AGENTS.md', '.github/copilot-instructions.md')
    run(repo, 'commit', '--no-verify', '-m', 'Merge default branch and regenerate guidance')
    return run(repo, 'rev-parse', 'HEAD').stdout.strip()


def push(source, repo, branch):
    # Push through the trusted checkout's configured credential, with ordinary non-force push.
    url = run(source, 'remote', 'get-url', 'origin').stdout.strip()
    run(repo, 'push', url, f'HEAD:refs/heads/{branch}')
