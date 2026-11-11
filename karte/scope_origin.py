"""scope の出所と reviewer 申告を区別する消費側向け API。"""

import secrets

from . import model, paths, scope_origin_store, scope_records
from .errors import KarteUsageError


def begin(issue, repo_root, accepted, source, round_no):
    entries = [{'id': e.finding_id, 'scope': e.item.scope, 'source': source, 'new': e.is_new}
               for e in accepted]
    event = {'tx': secrets.token_hex(16), 'phase': 'pending', 'round': round_no, 'entries': entries}
    scope_origin_store.append_event(issue, repo_root, event)
    return event


def commit(issue, repo_root, event):
    try:
        scope_origin_store.append_event(issue, repo_root, {**event, 'phase': 'committed'})
    except (OSError, paths.KartePathError, model.KarteFormatError) as exc:
        raise KarteUsageError(f'台帳は保存済みだが scope 出所の確定に失敗: {exc}。原因を解消し、再取り込みせず render で確認し activate で回復する') from exc


def first_writers(issue, repo_root):
    """ID -> main/reviewer/unknown。不完全な履歴や既存 finding は unknown。"""
    events = scope_origin_store.read_events(issue, repo_root)
    result = {}
    for i, event in enumerate(events):
        if event['phase'] != 'pending':
            continue
        complete = (i + 1 < len(events) and events[i + 1] == {**event, 'phase': 'committed'})
        for entry in event['entries']:
            if entry['id'] not in result:
                result[entry['id']] = entry['source'] if complete and entry['new'] else 'unknown'
    return result


def reviewer_declarations(issue, repo_root):
    """台帳への反映が確認できた reviewer 申告のみ返す。"""
    result = {}
    records = {(r, fid, scope) for _, (r, fid, scope, by) in scope_records.read_records(issue, repo_root) if not by}
    events = scope_origin_store.read_events(issue, repo_root)
    for i, event in enumerate(events):
        if event['phase'] != 'pending' or i + 1 >= len(events) or events[i + 1] != {**event, 'phase': 'committed'}:
            continue
        for entry in event['entries']:
            declaration = (event['round'], entry['id'], entry['scope'])
            if entry['source'] == 'reviewer' and declaration in records:
                result.setdefault(entry['id'], []).append((event['round'], entry['scope']))
    return result
