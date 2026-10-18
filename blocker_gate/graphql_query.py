"""単一queryだけを許可する、collector用GraphQL文書の狭い字句検査。"""

import json
import re


_TOKEN = re.compile(r"[_A-Za-z][_0-9A-Za-z]*|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|\.\.\.|[!$():=@\[\]{|}&]")
_IGNORED = re.compile(r"[\s,\ufeff]+|#[^\r\n]*")
_NAME = re.compile(r"[_A-Za-z][_0-9A-Za-z]*\Z")
_PAIRS = {"(": ")", "[": "]", "{": "}"}


def _tokens(document: str) -> list[str]:
    result: list[str] = []
    position = 0
    while position < len(document):
        ignored = _IGNORED.match(document, position)
        if ignored:
            position = ignored.end()
            continue
        if document.startswith('"""', position):
            raise ValueError("GraphQL block strings are unsupported")
        if document[position] == '"':
            _, position = json.JSONDecoder().raw_decode(document, position)
            result.append("<string>")
            continue
        token = _TOKEN.match(document, position)
        if not token:
            raise ValueError("Unsupported GraphQL token")
        result.append(token.group())
        position = token.end()
    return result


def _group_end(tokens: list[str], start: int) -> int:
    stack: list[str] = []
    for index in range(start, len(tokens)):
        token = tokens[index]
        if token in _PAIRS:
            stack.append(_PAIRS[token])
        elif token in _PAIRS.values():
            if not stack or stack.pop() != token:
                raise ValueError("Unbalanced GraphQL document")
            if not stack:
                return index + 1
    raise ValueError("Unterminated GraphQL group")


def validate_single_query(document: str) -> None:
    """明示queryを1つ許可する。block string・fragment定義・operation directiveは拒否。"""
    tokens = _tokens(document)
    if not tokens or tokens[0] != "query":
        raise ValueError("Only explicit GraphQL queries are permitted")
    position = 1
    if position < len(tokens) and _NAME.fullmatch(tokens[position]):
        position += 1
    if position < len(tokens) and tokens[position] == "(":
        position = _group_end(tokens, position)
    if position >= len(tokens) or tokens[position] != "{":
        raise ValueError("A query selection set is required")
    if _group_end(tokens, position) != len(tokens):
        raise ValueError("Only one GraphQL operation is permitted")
