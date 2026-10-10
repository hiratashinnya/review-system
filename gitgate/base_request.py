"""Strict arguments; callers cannot supply Git options or a merge strategy."""

import re
from branch_source.policy import validate_repository
from .base_error import require

VERBS = {"integrate-base", "integrate-base-continue", "integrate-base-abort"}


def parse_request(verb, args):
    require(verb in VERBS, "BASE_VERB_INVALID")
    if verb == "integrate-base-abort":
        require(not args, "BASE_ARGUMENT_INVALID")
        return {}
    if verb == "integrate-base-continue":
        modules = []
        while args:
            require(len(args) >= 2 and args[0] == "--test-module",
                    "BASE_ARGUMENT_INVALID")
            require(re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", args[1]),
                    "BASE_TEST_MODULE_INVALID")
            modules.append(args[1])
            args = args[2:]
        return {"test_modules": modules}
    values = {}
    flags = {"--repository", "--pr", "--expected-head", "--expected-base"}
    while args:
        require(len(args) >= 2 and args[0] in flags and args[0] not in values,
                "BASE_ARGUMENT_INVALID")
        values[args[0]] = args[1]
        args = args[2:]
    require(set(values) == flags, "BASE_ARGUMENT_INVALID")
    require(re.fullmatch(r"[1-9][0-9]*", values["--pr"]), "BASE_PR_INVALID")
    for flag in ("--expected-head", "--expected-base"):
        require(re.fullmatch(r"[0-9a-f]{40}", values[flag]), "BASE_OID_INVALID")
    return {"repository": validate_repository(values["--repository"]),
            "pr": int(values["--pr"]), "head": values["--expected-head"],
            "base": values["--expected-base"]}
