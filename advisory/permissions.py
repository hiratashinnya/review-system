"""CLI write gate: caller role must be established by the harness."""

import os


class PermissionDenied(ValueError):
    pass


def require_writer() -> str:
    if os.environ.get("ADVISORY_CALLER_ROLE") != "main-thread":
        raise PermissionDenied("only trusted main-thread can use advisory write verbs")
    return "main-thread"
