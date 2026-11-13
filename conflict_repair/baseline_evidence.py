"""未統合の baseline について、取得できた差分を判定と分離して記録する。"""
from .baseline_schema import SECTIONS, parse_baseline

_MISSING = object()


def _changes(old, new):
    return {'追加': sorted(new.keys() - old.keys()),
            '削除': sorted(old.keys() - new.keys()),
            '更新': sorted(key for key in new.keys() & old.keys() if new[key] != old[key])}


def describe(versions):
    parsed, errors = {}, {}
    for label, raw in zip(('祖先', 'main', 'head'), versions):
        try:
            if raw is None:
                raise ValueError('baseline を取得できません')
            parsed[label] = parse_baseline(raw)
        except ValueError as exc:
            errors[label] = str(exc)
    evidence = {'状態': '未統合', '解析エラー': errors, '各版の変更キー': {}, '競合キー': None}
    ancestor = parsed.get('祖先')
    for label in ('main', 'head'):
        side = parsed.get(label)
        evidence['各版の変更キー'][label] = (
            {section: _changes(ancestor[section], side[section]) for section in SECTIONS}
            if ancestor is not None and side is not None else None)
    if len(parsed) == 3:
        conflicts = {}
        for section in SECTIONS:
            old, main, head = (parsed[label][section] for label in ('祖先', 'main', 'head'))
            keys = old.keys() | main.keys() | head.keys()
            conflicts[section] = sorted(key for key in keys
                if main.get(key, _MISSING) != head.get(key, _MISSING)
                and main.get(key, _MISSING) != old.get(key, _MISSING)
                and head.get(key, _MISSING) != old.get(key, _MISSING))
        evidence['競合キー'] = conflicts
    return evidence
