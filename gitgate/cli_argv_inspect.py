"""Bounded inspect-verb argument builders for diff and log."""
from .cli_validation import GitgateError, validate_ref, validate_integer, validate_grep_pattern
def verb_diff(args):
    # `diff [--stat] [<ref>...]` → `git diff [--stat] [<ref>...]`。
    # 受け付けるフラグは `--stat` のみ（`--output` 等の write 系フラグは一切受け付けない）。
    argv = ["git", "diff"]
    stat_seen = False
    for a in args:
        if a == "--stat":
            if not stat_seen:
                argv.append("--stat")
                stat_seen = True
            continue
        if a.startswith("-"):
            raise GitgateError(f"`diff` only accepts the `--stat` flag; unexpected flag: {a!r}")
        argv.append(validate_ref(a))
    return argv


def verb_log(args):
    # `log [-n <N>] [--grep <pat>] [--oneline]` → `git log …`。フラグは固定集合のみ、位置引数は不可。
    argv = ["git", "log"]
    i = 0
    seen = set()
    while i < len(args):
        a = args[i]
        if a == "-n":
            if i + 1 >= len(args):
                raise GitgateError("`log -n` requires an integer argument")
            n = validate_integer(args[i + 1])
            argv += ["-n", n]
            i += 2
            continue
        if a.startswith("-n") and len(a) > 2:
            # `-n5` の連結形
            n = validate_integer(a[2:])
            argv += ["-n", n]
            i += 1
            continue
        if a == "--grep":
            if i + 1 >= len(args):
                raise GitgateError("`log --grep` requires a pattern argument")
            pat = validate_grep_pattern(args[i + 1])
            argv.append("--grep=" + pat)
            i += 2
            continue
        if a.startswith("--grep="):
            pat = validate_grep_pattern(a[len("--grep="):])
            argv.append("--grep=" + pat)
            i += 1
            continue
        if a == "--oneline":
            if "--oneline" not in seen:
                argv.append("--oneline")
                seen.add("--oneline")
            i += 1
            continue
        raise GitgateError(
            f"`log` only accepts `-n <N>`, `--grep <pat>` and `--oneline`; unexpected argument: {a!r}"
        )
    return argv
