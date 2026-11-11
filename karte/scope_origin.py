"""scope の出所と reviewer 申告を区別する消費側向け API。"""

import secrets

from . import scope_origin_store, scope_records


def begin(issue, repo_root, accepted, source):
    entries = [{'id': e.finding_id, 'scope': e.item.scope, 'source': source, 'new': e.is_new}
               for e in accepted]
    event = {'tx': secrets.token_hex(16), 'phase': 'pending', 'entries': entries}
    scope_origin_store.append_event(issue, repo_root, event)
    return event


def commit(issue, repo_root, event):
    scope_origin_store.append_event(issue, repo_root, {**event, 'phase': 'committed'})


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
    """ID -> reviewer の申告履歴。存在しない ID は未証明として扱う。"""
    result = {}
    for _line, (round_no, finding_id, scope, by) in scope_records.read_records(issue, repo_root):
        if not by:
            result.setdefault(finding_id, []).append((round_no, scope))
    return result
