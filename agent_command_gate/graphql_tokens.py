"""Recognize GraphQL mutation operations while skipping comments and strings."""

MERGE_MUTATIONS = {"mergePullRequest", "enablePullRequestAutoMerge"}


def contains_mutation(source, *, merge_only=False):
    index = depth = 0
    mutation = False
    while index < len(source):
        if source.startswith('"""', index):
            end = source.find('"""', index + 3)
            index = len(source) if end < 0 else end + 3
            continue
        char = source[index]
        if char == '"':
            index += 1
            while index < len(source) and source[index] != '"':
                index += 2 if source[index] == "\\" else 1
            index = min(index + 1, len(source))
            continue
        if char == "#":
            end = source.find("\n", index)
            index = len(source) if end < 0 else end + 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth = max(0, depth - 1)
        if char.isascii() and (char.isalnum() or char == "_"):
            end = index + 1
            while end < len(source) and source[end].isascii() and (source[end].isalnum() or source[end] == "_"):
                end += 1
            name = source[index:end]
            if depth == 0 and name == "mutation":
                if not merge_only:
                    return True
                mutation = True
            elif mutation and depth == 1 and name in MERGE_MUTATIONS:
                return True
            index = end
        else:
            index += 1
    return False
