"""外部 JSON の曖昧なキーと非標準数値を拒否する。"""

import json


def load_json(text: str) -> object:
    """重複キーは階層を問わず失敗とし、後続値で拒否を消させない。"""
    try:
        return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except RecursionError:
        raise ValueError("json_nesting_invalid") from None


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("json_duplicate_key")
        result[name] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("json_nonstandard_constant")
