"""Inspect GitHub API calls only for merge mutations."""

from urllib.parse import urlsplit

from .github_graphql import graphql_merge_reason


READ_METHODS = {"GET", "HEAD"}


def _route_is_pull_merge(route):
    parts = [part.lower() for part in urlsplit(route).path.split("/") if part]
    return any(
        parts[index] == "pulls"
        and parts[index + 1].isdigit()
        and parts[index + 2] == "merge"
        for index in range(max(0, len(parts) - 2))
    )


def merge_api_reason(arguments):
    method = None
    endpoints = []
    fields = []
    input_path = None
    has_body = False
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token in {"-X", "--method", "--input"}:
            if index + 1 >= len(arguments):
                return "an API option is missing its value"
            value = arguments[index + 1]
            if token == "--input":
                input_path, has_body = value, True
            elif token == "-X":
                method = value.upper()
            else:
                method = value.upper()
            index += 2
            continue
        if token.startswith("--method="):
            method = token.partition("=")[2].upper()
        elif token.startswith("--input="):
            input_path, has_body = token.partition("=")[2], True
        elif token.startswith("--field=") or token.startswith("--raw-field="):
            field_flag = token.partition("=")[0]
            key, separator, content = token.partition("=")[2].partition("=")
            if separator:
                fields.append((key, content, field_flag == "--field"))
            has_body = True
        elif token in {"-f", "-F", "--field", "--raw-field"}:
            if index + 1 >= len(arguments):
                return "an API field option is missing its value"
            value = arguments[index + 1]
            key, separator, content = value.partition("=")
            if separator:
                fields.append((key, content, token in {"-F", "--field"}))
            has_body = True
            index += 2
            continue
        elif token.startswith(("-f", "-F")) and len(token) > 2:
            field_flag = token[:2]
            key, separator, content = token[2:].partition("=")
            if separator:
                fields.append((key, content, field_flag == "-F"))
            has_body = True
        elif token.startswith("-X") and len(token) > 2:
            method = token[2:].upper()
        elif not token.startswith("-"):
            endpoints.append(token)
        index += 1

    actual_method = method or ("POST" if has_body else "GET")
    if any("$" in endpoint or "`" in endpoint for endpoint in endpoints):
        return "the GitHub API endpoint is dynamically supplied and cannot be inspected"
    if any(_route_is_pull_merge(route) for route in endpoints):
        if actual_method not in READ_METHODS:
            return "the GitHub REST request targets a pull request merge route with a write method"

    graphql = any("graphql" in urlsplit(route).path.lower().split("/") for route in endpoints)
    if not graphql:
        return None
    return graphql_merge_reason(endpoints, fields, input_path)
