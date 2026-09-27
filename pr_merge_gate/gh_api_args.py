"""`gh api` の引数をmerge判定用の構造へ正規化する。"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


_VALUE_OPTIONS = frozenset(
    {"--cache", "-H", "--header", "-q", "--jq", "-p", "--preview", "-t", "--template"}
)
_SWITCH_OPTIONS = frozenset(
    {"-i", "--include", "--paginate", "--silent", "--slurp", "--verbose", "--help"}
)
_ATTACHED_VALUE_PREFIXES = tuple(
    option + "=" for option in _VALUE_OPTIONS if option.startswith("--")
)
_DEFERRED_VALUE_OPTIONS = frozenset({"--hostname", "--input"})

@dataclass(frozen=True)
class _GhApiArguments:
    endpoint: str | None
    method: str
    fields: Mapping[str, str]
    typed_fields: frozenset[str]
    deferred_options: frozenset[str]


def _record_field(raw: str, typed: bool, fields: dict[str, str], typed_fields: set[str]) -> None:
    if "=" not in raw:
        raise ValueError("field")
    key, value = raw.split("=", 1)
    if key in fields:
        raise ValueError("field")
    fields[key] = value
    if typed:
        typed_fields.add(key)


def _parse_gh_api_arguments(tokens: list[str]) -> _GhApiArguments:
    endpoint: str | None = None
    method = "GET"
    fields: dict[str, str] = {}
    typed_fields: set[str] = set()
    deferred_options: set[str] = set()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"-X", "--method"}:
            if index + 1 >= len(tokens):
                raise ValueError("method")
            method = tokens[index + 1].upper()
            index += 2
        elif token.startswith("-X") and len(token) > 2:
            method = token[2:].upper()
            index += 1
        elif token.startswith("--method="):
            method = token.split("=", 1)[1].upper()
            index += 1
        elif token in {"-f", "--raw-field", "-F", "--field"}:
            if index + 1 >= len(tokens):
                raise ValueError("field")
            _record_field(
                tokens[index + 1], token in {"-F", "--field"}, fields, typed_fields
            )
            index += 2
        elif token.startswith(("--raw-field=", "--field=")) or (
            token.startswith(("-f", "-F")) and "=" in token[2:]
        ):
            if token.startswith("--raw-field="):
                raw, typed = token.removeprefix("--raw-field="), False
            elif token.startswith("--field="):
                raw, typed = token.removeprefix("--field="), True
            else:
                raw, typed = token[2:], token.startswith("-F")
            _record_field(raw, typed, fields, typed_fields)
            index += 1
        elif token in _SWITCH_OPTIONS or token.startswith(_ATTACHED_VALUE_PREFIXES):
            index += 1
        elif token in _VALUE_OPTIONS | _DEFERRED_VALUE_OPTIONS:
            if index + 1 >= len(tokens):
                raise ValueError("option")
            if token in _DEFERRED_VALUE_OPTIONS:
                deferred_options.add(token)
            index += 2
        elif token.startswith(("--hostname=", "--input=")):
            deferred_options.add(token.split("=", 1)[0])
            index += 1
        elif token.startswith("-"):
            index += 1
        elif endpoint is None:
            endpoint = token
            index += 1
        else:
            raise ValueError("endpoint")
    return _GhApiArguments(
        endpoint, method, MappingProxyType(fields),
        frozenset(typed_fields), frozenset(deferred_options),
    )
