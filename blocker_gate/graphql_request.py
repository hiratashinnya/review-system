"""JSONの解析差やoperation選択を持たないGraphQL queryリクエスト検査。"""

import json
import math

from .graphql_query import validate_single_query


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON keys are forbidden")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ValueError("Non-finite JSON numbers are forbidden")


def _finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite JSON numbers are forbidden")
    return result


def validate_read_request(body: bytes) -> None:
    """UTF-8 JSONのqueryと任意のvariablesだけを許可し、契約違反はValueError。"""
    if not isinstance(body, bytes):
        raise ValueError("The GraphQL body must be UTF-8 bytes")
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant, parse_float=_finite_float)
        if not isinstance(value, dict) or not {"query"} <= value.keys() <= {"query", "variables"}:
            raise ValueError("Only query and optional variables are permitted")
        if not isinstance(value["query"], str) or not isinstance(value.get("variables", {}), dict):
            raise ValueError("Invalid query or variables type")
        validate_single_query(value["query"])
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid GraphQL request encoding or nesting") from exc
