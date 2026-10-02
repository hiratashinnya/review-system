"""Inspect inline and file-backed GraphQL request bodies."""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .graphql_tokens import contains_merge_mutation

MAX_BODY_BYTES = 1_000_000


def _read_payload(path):
    if path == "-":
        return None, "the API payload comes from stdin and cannot be inspected"
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None, "the API payload file cannot be read"
    if len(data) > MAX_BODY_BYTES:
        return None, "the API payload exceeds the inspection limit"
    try:
        return data.decode("utf-8"), None
    except UnicodeError:
        return None, "the API payload is not valid UTF-8"


def _query_from_input(path):
    body, error = _read_payload(path)
    if error:
        return None, error
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None, "the GraphQL input file is not valid JSON"
    query = payload.get("query") if isinstance(payload, dict) else None
    if not isinstance(query, str):
        return None, "the GraphQL input file has no inspectable query string"
    return query, None


def graphql_merge_reason(endpoints, fields, input_path):
    queries = []
    for endpoint in endpoints:
        queries.extend(parse_qs(urlsplit(endpoint).query).get("query", []))
    for key, content, accepts_file in fields:
        if key != "query":
            continue
        if content.startswith("@") and accepts_file:
            content, error = _read_payload(content[1:])
            if error:
                return error
        elif content.startswith("$"):
            return "the GraphQL query is dynamically supplied and cannot be inspected"
        queries.append(content)
    if input_path:
        query, error = _query_from_input(input_path)
        if error:
            return error
        queries.append(query)
    if any(contains_merge_mutation(query) for query in queries):
        return "the GraphQL request contains a pull request merge mutation"
    return None
