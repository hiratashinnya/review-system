"""既存 baseline 値だけを用いた fail-closed な 3-way 統合。"""
from .baseline_schema import SECTIONS, parse_baseline

_MISSING = object()


def merge_baselines(ancestor_raw, main_raw, head_raw):
    ancestor, main, head = map(parse_baseline, (ancestor_raw, main_raw, head_raw))
    if any(ancestor[key] != side[key] for side in (main, head)
           for key in ('schema_version', 'source')):
        raise ValueError('baseline metadata differs')
    result = {key: ancestor[key] for key in ('schema_version', 'source')}
    for section in SECTIONS:
        original, left, right = (version[section] for version in (ancestor, main, head))
        merged = {}
        for key in sorted(original.keys() | left.keys() | right.keys()):
            old, base, branch = (entries.get(key, _MISSING)
                                 for entries in (original, left, right))
            if base == branch:
                chosen = base
            elif base == old:
                chosen = branch
            elif branch == old:
                chosen = base
            else:
                raise ValueError(f'baseline conflict: {section} {key}')
            if chosen is not _MISSING:
                merged[key] = chosen
        result[section] = merged
    return result
