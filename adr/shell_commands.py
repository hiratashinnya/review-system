"""通知対象rootをshellのsubshell・pipelineスコープごとに導出する。"""
import re
import shlex


def command_roots(command, cwd):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace = " \t\r"
    tokens = []
    for token in lexer:
        if token and all(char in ";&|()\n" for char in token):
            tokens.extend(re.findall(r"&&|\|\||\|&|[;&|()\n]", token))
        else:
            tokens.append(token)
    return sequence_roots(tokens, cwd)[0]


def command_groups(tokens, separators):
    depth, group = 0, []
    for token in tokens:
        if depth == 0 and token in separators:
            yield group, token
            group = []
            continue
        depth += (token == "(") - (token == ")")
        group.append(token)
    yield group, ""


def sequence_roots(tokens, cwd):
    roots = set()
    for group, separator in command_groups(tokens, {";", "&&", "||", "&", "\n"}):
        found, next_cwd = pipeline_roots(group, cwd)
        roots.update(found)
        if separator != "&":
            cwd = next_cwd
    return roots, cwd


def pipeline_roots(tokens, cwd):
    branches = list(command_groups(tokens, {"|", "|&"}))
    roots, next_cwd = set(), cwd
    for branch, _ in branches:
        found, branch_cwd = simple_roots(branch, cwd)
        roots.update(found)
        if len(branches) == 1:
            next_cwd = branch_cwd
    return roots, next_cwd


def simple_roots(tokens, cwd):
    if tokens[:1] == ["("]:
        found, _ = sequence_roots(tokens[1:-1], cwd)
        return found, cwd
    if tokens[:1] == ["cd"]:
        arguments = [part for part in tokens[1:] if part != "--"]
        if len(arguments) == 1 and (cwd / arguments[0]).is_dir():
            return set(), (cwd / arguments[0]).resolve()
    roots = set()
    for position in range(len(tokens) - 2):
        if tokens[position:position + 2] != ["-m", "adr"]:
            continue
        tail = tokens[position + 2:]
        if tail[0] not in ("new-entry", "file-issue"):
            continue
        for index, argument in enumerate(tail):
            if argument == "--root" and index + 1 < len(tail):
                roots.add(cwd / tail[index + 1])
            elif argument.startswith("--root="):
                roots.add(cwd / argument.split("=", 1)[1])
    return roots, cwd
