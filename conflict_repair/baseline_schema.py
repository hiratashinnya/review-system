"""競合修復が受理する baseline の構造を検査する。"""
import json
import re

SECTIONS = ("module_lines", "comment_blocks", "mixed_class_files")
KEYS = {"schema_version", "source", *SECTIONS}
HASH = re.compile(r"[0-9a-f]{64}\Z")
COMMENT = re.compile(r".+\.py\|[0-9a-f]{16}\Z")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _path(key):
    return (isinstance(key, str) and key.endswith('.py') and not key.startswith('/')
            and all(part not in ('', '.', '..') for part in key.split('/')))


def _hash(value):
    return isinstance(value, str) and HASH.fullmatch(value) is not None


def _positive(value):
    return type(value) is int and value > 0


def _entry(section, key, value):
    if section == 'comment_blocks':
        return (isinstance(key, str) and COMMENT.fullmatch(key) is not None
                and _path(key.rsplit('|', 1)[0]) and _positive(value))
    if not _path(key) or not isinstance(value, dict):
        return False
    if section == 'module_lines':
        return (set(value) == {'line_count', 'sha256'}
                and _positive(value['line_count']) and _hash(value['sha256']))
    return (set(value) == {'data', 'logic', 'sha256'} and _hash(value['sha256'])
            and all(isinstance(value[k], list) and value[k]
                    and all(isinstance(name, str) and name for name in value[k])
                    for k in ('data', 'logic')))


def parse_baseline(raw):
    try:
        data = json.loads(raw, object_pairs_hook=_object)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f'invalid baseline JSON: {exc}') from exc
    if (not isinstance(data, dict) or set(data) != KEYS
            or type(data['schema_version']) is not int or data['schema_version'] != 2
            or not isinstance(data['source'], str) or not data['source']):
        raise ValueError('invalid baseline metadata')
    for section in SECTIONS:
        entries = data[section]
        if not isinstance(entries, dict) or any(
                not _entry(section, key, value) for key, value in entries.items()):
            raise ValueError(f'invalid baseline section: {section}')
    return data
