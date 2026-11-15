"""scope の書き手を台帳更新の前後に記録する補助台帳。"""

import json
from pathlib import Path

from . import paths
from .scope_atomic import write_scope_text
from .scope_directory import open_scope_directory
from .scope_ledger_io import read_scope_text
from .model import KarteFormatError


def origin_path(issue, repo_root):
    return Path(repo_root).resolve() / 'tmp' / '_karte' / f'issue-{paths.validate_issue(issue)}.scope-origin.jsonl'


def read_events(issue, repo_root):
    path = origin_path(issue, repo_root)
    try:
        with open_scope_directory(path) as directory:
            text = read_scope_text(path, directory)
    except paths.KarteMissing:
        return []
    events = []
    for line in (text or '').splitlines():
        try:
            event = json.loads(line)
            if (not isinstance(event, dict) or set(event) != {'tx', 'phase', 'round', 'entries'}
                    or not isinstance(event['tx'], str) or not event['tx']
                    or event['phase'] not in ('pending', 'committed')
                    or type(event['round']) is not int or event['round'] < 1
                    or not isinstance(event['entries'], list)):
                raise ValueError('invalid event')
            for entry in event['entries']:
                if (not isinstance(entry, dict) or set(entry) != {'id', 'scope', 'source', 'new'}
                        or not isinstance(entry['id'], str) or entry['scope'] not in ('in', 'out')
                        or entry['source'] not in ('main', 'reviewer') or type(entry['new']) is not bool):
                    raise ValueError('invalid entry')
            events.append(event)
        except (ValueError, TypeError, RecursionError) as exc:
            raise KarteFormatError(f'scope 出所記録が壊れている: {path}: {exc}') from None
    return events


def append_event(issue, repo_root, event):
    path = origin_path(issue, repo_root)
    with open_scope_directory(path, create=True) as directory:
        current = read_scope_text(path, directory)
        read_events(issue, repo_root)
        line = json.dumps(event, ensure_ascii=False, separators=(',', ':'))
        write_scope_text(path, directory, (current or '') + line + '\n', expected=current)
