"""Validate the pinned triager execution profile's safety properties."""
import tomllib


def verify_readonly_profile(worktree):
    data = tomllib.loads((worktree / '.codex/config.toml').read_text())
    profile = data['permissions']['adviser']
    if set(profile) != {'extends', 'network', 'filesystem'} or profile.get('extends') != ':read-only':
        raise ValueError('triager profile must be read-only')
    network = profile.get('network', {})
    network_keys = {'enabled', 'allow_local_binding', 'dangerously_allow_all_unix_sockets',
                    'dangerously_allow_non_loopback_proxy'}
    if set(network) != network_keys or any(network[k] is not False for k in network_keys):
        raise ValueError('triager profile must deny network')
    filesystem = profile.get('filesystem', {})
    denied = {'~/.codex/auth.json', '~/.config/gh', '~/.claude/.credentials.json', '~/.ssh'}
    if set(filesystem) != denied or any(filesystem[k] != 'deny' for k in denied):
        raise ValueError('triager profile must deny credentials')
