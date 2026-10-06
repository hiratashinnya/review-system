"""Skip known Git and GitHub CLI global options before inspecting subcommands."""

import shlex


GIT_VALUES = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env", "--super-prefix", "--shallow-file"}
GIT_FLAGS = {"--no-pager", "--paginate", "--no-replace-objects", "--literal-pathspecs", "--glob-pathspecs", "--noglob-pathspecs", "--icase-pathspecs", "--no-optional-locks", "--bare", "-p", "-v"}
GH_VALUES = {"-R", "--repo", "--hostname", "--config", "--profile"}
GH_FLAGS = {"--help", "--version"}


def _alias_merges(value):
    key, separator, command = value.partition("=")
    if not separator or not key.startswith("alias."):
        return False
    try:
        return "merge" in shlex.split(command)
    except ValueError:
        return True


def skip_global_options(tokens, executable, start_index=1):
    valued = GIT_VALUES if executable == "git" else GH_VALUES
    flags = GIT_FLAGS if executable == "git" else GH_FLAGS
    index = start_index
    while index < len(tokens) and tokens[index].startswith("-"):
        token = tokens[index]
        option, equals, _ = token.partition("=")
        if option in valued:
            if not equals and index + 1 >= len(tokens):
                return None, "a global option is missing its value"
            value = token if equals else tokens[index + 1]
            if equals:
                value = token.partition("=")[2]
            if executable == "git" and option == "-c" and _alias_merges(value):
                return None, "a command-line Git alias explicitly invokes merge"
            if executable == "git" and option == "--config-env" and value.partition("=")[0].startswith("alias."):
                return None, "a Git alias value supplied by the environment cannot be inspected"
            index += 1 if equals else 2
        elif executable == "gh" and token.startswith("-R") and len(token) > 2:
            index += 1
        elif token in flags:
            index += 1
        elif executable == "git" and token.startswith(("-C", "-c")) and len(token) > 2:
            if token.startswith("-c") and _alias_merges(token[2:]):
                return None, "a command-line Git alias explicitly invokes merge"
            index += 1
        else:
            return None, f"the global option {token!r} cannot be inspected safely"
    return index, None
