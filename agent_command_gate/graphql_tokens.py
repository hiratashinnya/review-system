"""Recognize merge mutation names in GraphQL operation selection sets."""


MERGE_MUTATIONS = {"mergePullRequest", "enablePullRequestAutoMerge"}


def contains_merge_mutation(source):
    word = []
    index = 0
    brace_depth = 0
    mutation = False
    while index < len(source):
        char = source[index]
        if source.startswith('"""', index):
            end = source.find('"""', index + 3)
            index = len(source) if end < 0 else end + 3
            continue
        if char == '"':
            index += 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                elif source[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            continue
        if char == "#":
            end = source.find("\n", index)
            index = len(source) if end < 0 else end + 1
            continue
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth = max(0, brace_depth - 1)
        if char.isascii() and (char.isalnum() or char == "_"):
            word.append(char)
        else:
            name = "".join(word)
            if name == "mutation" and brace_depth == 0:
                mutation = True
            if mutation and brace_depth == 1 and name in MERGE_MUTATIONS:
                return True
            word.clear()
        index += 1
    return False
