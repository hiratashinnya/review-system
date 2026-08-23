"""Managed merge tool input の closed classifier。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import stat
import subprocess
from typing import Any, Callable, Literal, Mapping, Sequence, cast

from blocker_gate.model import fingerprint


_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_HTTPS_REMOTE = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$")
_SSH_REMOTE = re.compile(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$")
_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_REST_MERGE = re.compile(
    r"^/?repos/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/pulls/([1-9][0-9]*)/merge$"
)
CLASSIFIER_VERSION = "1.13"
_MAX_GRAPHQL_QUERY_BYTES = 1_048_576
_SAFE_DATA_EXECUTABLES = frozenset({"echo", "printf", "pwd", "true", "false"})
_SHELL_CONTROL_RESERVED_WORDS = frozenset(
    {
        "!", "[[", "]]", "case", "coproc", "do", "done", "elif", "else", "esac", "fi", "for",
        "function", "if", "in", "select", "then", "time", "until", "while",
    }
)
_SHELL_EVALUATORS = frozenset({"bash", "sh", "zsh", "fish"})
_SHELL_SHORT_OPTIONS = {
    "bash": frozenset("abefhiklmnpstuvxBCEHPTlrD"),
    "sh": frozenset("abefhiklmnpstuvx"),
    "zsh": frozenset("cdfiklnrstuvx"),
    "fish": frozenset("cdfilnNpPv"),
}
_SHELL_LONG_NO_ARG_OPTIONS = {
    "bash": frozenset(
        {"--debugger", "--login", "--noediting", "--noprofile", "--norc", "--posix", "--restricted", "--verbose"}
    ),
    "sh": frozenset(),
    "zsh": frozenset({"--globalrcs", "--no-globalrcs", "--no-rcs", "--rcs"}),
    "fish": frozenset({"--interactive", "--login", "--no-config", "--no-execute", "--private"}),
}
_SHELL_LONG_VALUE_OPTIONS = {
    "bash": frozenset({"--init-file", "--rcfile"}),
    "sh": frozenset(),
    "zsh": frozenset(),
    "fish": frozenset({"--debug", "--debug-output", "--profile", "--profile-startup"}),
}
_SHELL_COMMAND_LONG_OPTIONS = {"fish": frozenset({"--command"})}
_SHELL_UNSUPPORTED_EVALUATING_OPTIONS = {"fish": frozenset({"--init-command"})}
_TRUSTED_GIT_EXECUTABLES = frozenset({"git", "/bin/git", "/usr/bin/git"})
_TRUSTED_ABSOLUTE_GIT_EXECUTABLES = frozenset({"/bin/git", "/usr/bin/git"})
_HARMLESS_ENVIRONMENT_VARIABLES = frozenset({"LANG", "LANGUAGE", "LC_ALL"})
_SHELL_STATE_COMMANDS = frozenset(
    {
        ".", "alias", "bg", "bind", "break", "cd", "complete", "compopt", "continue", "declare",
        "dirs", "disown", "enable", "exec", "exit", "export", "fc", "fg", "getopts", "hash",
        "history", "jobs", "kill", "let", "local", "logout", "mapfile", "popd", "pushd", "read",
        "readarray", "readonly", "return", "set", "shift", "shopt", "source", "suspend", "trap",
        "typeset", "ulimit", "umask", "unalias", "unset", "wait",
    }
)
_SAFE_GIT_BUILTINS = frozenset(
    {
        "add", "am", "apply", "archive", "bisect", "blame", "branch", "bundle", "checkout", "cherry-pick",
        "clean", "clone", "commit", "config", "describe", "diff", "fetch", "format-patch", "fsck", "gc",
        "grep", "init", "log", "ls-files", "ls-remote", "merge", "merge-base", "mv", "notes", "pull",
        "push", "range-diff", "rebase", "reflog", "remote", "repack", "replace", "reset", "restore", "revert",
        "rev-list", "rev-parse", "rm", "shortlog", "show", "show-ref", "sparse-checkout", "stash", "status",
        "switch", "tag", "verify-commit", "verify-tag", "worktree",
    }
)
_GIT_SHELL_EVALUATING_OPTIONS = frozenset(
    {
        "--config-env", "--exec", "--ext-diff", "--open-files-in-pager", "--receive-pack",
        "--reschedule-failed-exec", "--ssh-command", "--textconv", "--upload-pack",
    }
)
_GIT_SHELL_EVALUATING_SHORT_OPTIONS = {
    "clone": frozenset({"u"}),
    "grep": frozenset({"O"}),
    "rebase": frozenset({"x"}),
}
_GH_NON_MERGE_COMMANDS = frozenset(
    {
        "auth", "browse", "codespace", "completion", "config", "gist", "issue", "label",
        "release", "repo", "run", "search", "secret", "ssh-key", "status", "variable",
        "workflow",
    }
)
_GH_NON_MERGE_PR_COMMANDS = frozenset(
    {
        "checks", "checkout", "close", "comment", "create", "diff", "edit", "list", "lock",
        "ready", "reopen", "review", "status", "unlock", "update-branch", "view",
    }
)
_SAFE_ALIAS_FLAGS = frozenset({"--shell"})
_CONNECTOR_MERGE = frozenset(
    {
        "github_merge_pull_request",
        "codex_apps.github.merge_pull_request",
        "mcp__github__merge_pull_request",
        "mcp__codex_apps__github_merge_pull_request",
    }
)
_CONNECTOR_AUTO = frozenset(
    {
        "github_enable_auto_merge",
        "codex_apps.github.enable_auto_merge",
        "mcp__github__enable_auto_merge",
        "mcp__github__enable_pull_request_auto_merge",
        "mcp__codex_apps__github_enable_auto_merge",
    }
)


@dataclass(frozen=True)
class MergeOperation:
    """同じ intercepted invocation に束縛した即時merge操作。"""

    repository: str
    pr_number: int
    merge_method: Literal["merge", "rebase", "squash"]
    transport: Literal["cli-direct", "cli-wrapped", "rest", "connector"]
    commit_title: str | None
    commit_message: str | None
    expected_head_oid: str | None
    operation_fingerprint: str


@dataclass(frozen=True)
class PreUseClassification:
    """closed classifier の merge/block/error 結果。"""

    kind: Literal["merge", "block", "error"]
    reason: str
    operation: MergeOperation | None
    operation_fingerprint: str


def _error(reason: str, raw: Any) -> PreUseClassification:
    return PreUseClassification("error", reason, None, fingerprint({"raw": raw}))


def _block(reason: str, raw: Any) -> PreUseClassification:
    return PreUseClassification("block", reason, None, fingerprint({"raw": raw}))


def _canonical_repository(value: str) -> str:
    if not _REPOSITORY.fullmatch(value) or value.endswith(".git"):
        raise ValueError("repository")
    return value


def repository_from_cwd(
    payload: Mapping[str, Any],
    *,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    """hook payloadのcwdとexact worktree originからcanonical repositoryを得る。"""
    payload_cwd = payload.get("cwd")
    if not isinstance(payload_cwd, str) or not Path(payload_cwd).is_absolute():
        raise ValueError("cwd")
    try:
        payload_root = Path(payload_cwd).resolve(strict=True)
        hook_root = (Path.cwd() if cwd is None else cwd).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("cwd") from exc
    if payload_root != hook_root or not hook_root.is_dir():
        raise ValueError("cwd")

    def run_git(argv: Sequence[str]) -> str:
        try:
            completed = runner(
                list(argv), cwd=str(hook_root), text=True, capture_output=True, shell=False
            )
        except OSError as exc:
            raise ValueError("git") from exc
        output = completed.stdout
        if completed.returncode != 0 or not isinstance(output, str) or "\0" in output:
            raise ValueError("git")
        output = output.rstrip("\n")
        if "\n" in output or "\r" in output:
            raise ValueError("git")
        return output

    if run_git(["git", "rev-parse", "--show-toplevel"]) != str(hook_root):
        raise ValueError("worktree")
    remote = run_git(["git", "remote", "get-url", "origin"])
    for pattern in (_HTTPS_REMOTE, _SSH_REMOTE):
        match = pattern.fullmatch(remote)
        if match is not None:
            return _canonical_repository(f"{match.group(1)}/{match.group(2)}")
    raise ValueError("origin")


def _unwrap(tokens: list[str]) -> tuple[list[str], list[str]]:
    wrappers: list[str] = []
    remaining = list(tokens)
    while remaining and remaining[0] in {"rtk", "command", "builtin", "exec"}:
        wrapper = remaining.pop(0)
        wrappers.append(wrapper)
        if wrapper == "rtk" and remaining and remaining[0] == "proxy":
            wrappers.append(remaining.pop(0))
        elif wrapper in {"command", "builtin", "exec"} and remaining and remaining[0] == "--":
            remaining.pop(0)
    return remaining, wrappers


def _command_environment(
    tokens: list[str],
) -> tuple[list[str], list[str], dict[str, str], bool] | None:
    """Shell prefixとenv wrapperを解析し、実行commandへ作用する環境を保持する。"""
    remaining = list(tokens)
    assignments: dict[str, str] = {}
    while remaining:
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", remaining[0], flags=re.DOTALL)
        if match is None:
            break
        assignments[match.group(1)] = match.group(2)
        remaining.pop(0)

    remaining, wrappers = _unwrap(remaining)
    ignore_environment = False
    if remaining and remaining[0] == "env":
        wrappers.append("env")
        index = 1
        while index < len(remaining):
            token = remaining[index]
            if token == "--":
                index += 1
                break
            if token in {"-i", "--ignore-environment"}:
                ignore_environment = True
                index += 1
                continue
            if token.startswith("-"):
                return None
            match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", token, flags=re.DOTALL)
            if match is None:
                break
            assignments[match.group(1)] = match.group(2)
            index += 1
        while index < len(remaining):
            match = re.fullmatch(
                r"([A-Za-z_][A-Za-z0-9_]*)=(.*)",
                remaining[index],
                flags=re.DOTALL,
            )
            if match is None:
                break
            assignments[match.group(1)] = match.group(2)
            index += 1
        remaining = remaining[index:]
        remaining, nested_wrappers = _unwrap(remaining)
        wrappers.extend(nested_wrappers)
    return remaining, wrappers, assignments, ignore_environment


def _environment_allows_executable(
    assignments: Mapping[str, str],
    *,
    ignore_environment: bool,
    executable: str,
) -> bool:
    """実行実体やGitの外部commandを差し替えない環境だけを許可する。"""
    names = set(assignments)
    harmless = all(
        name in _HARMLESS_ENVIRONMENT_VARIABLES or re.fullmatch(r"LC_[A-Z0-9_]+", name)
        for name in names
    )
    if harmless and not ignore_environment:
        return True
    if executable in _SAFE_DATA_EXECUTABLES and not ignore_environment:
        return all(
            name not in {"BASH_ENV", "ENV", "PATH", "SHELLOPTS"}
            and not name.startswith(("DYLD_", "GIT_", "LD_"))
            for name in names
        )
    if executable not in _TRUSTED_ABSOLUTE_GIT_EXECUTABLES:
        return False
    return all(
        name == "PATH"
        or name in _HARMLESS_ENVIRONMENT_VARIABLES
        or re.fullmatch(r"LC_[A-Z0-9_]+", name)
        for name in names
    )


def _state_independent_data_shape(tokens: list[str]) -> bool:
    """親shellを変更しないとclosed grammarで証明できるdata commandだけを返す。"""
    if not tokens or tokens[0] not in _SAFE_DATA_EXECUTABLES:
        return False
    if tokens[0] != "printf":
        return True
    return len(tokens) == 1 or tokens[1] == "--" or not tokens[1].startswith("-")


def _compound_changes_shell_state(command: str) -> bool:
    """後続leafの実行実体へ状態を持ち越し得るcompound leafを検出する。"""
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return True
    if not tokens:
        return True
    environment = _command_environment(tokens)
    if environment is None:
        return True
    remaining, wrappers, assignments, _ = environment
    if not remaining:
        return bool(assignments) and "env" not in wrappers
    if "exec" in wrappers or remaining[0] == "eval":
        return True
    if remaining[0] in _SAFE_DATA_EXECUTABLES:
        return not _state_independent_data_shape(remaining)
    return remaining[0] in _SHELL_STATE_COMMANDS


def _split_shell_commands(command: str) -> list[str] | None:
    """proof可能なsimple/linear shellだけをquote-awareに分割する。Noneは未対応構造。"""
    commands: list[str] = []
    quote: str | None = None
    escaped = False
    head_word: list[str] = []
    head_word_quoted = False
    head_word_checked = False
    start = 0
    index = 0
    while index < len(command):
        character = command[index]
        if escaped:
            if not head_word_checked:
                head_word.append(character)
            escaped = False
            index += 1
            continue
        if quote == "'":
            if character == "'":
                quote = None
            elif not head_word_checked:
                head_word.append(character)
            index += 1
            continue
        if character == "\\":
            if index + 1 < len(command) and command[index + 1] in "\n\r":
                index += 2
                continue
            if not head_word_checked:
                head_word_quoted = True
            escaped = True
            index += 1
            continue
        if quote == '"':
            if character == '"':
                quote = None
            elif character == "`" or (character == "$" and command[index:index + 2] == "$("):
                return None
            elif not head_word_checked:
                head_word.append(character)
            index += 1
            continue
        if character in {"'", '"'}:
            if not head_word_checked:
                head_word_quoted = True
            quote = character
            index += 1
            continue
        if character == "`" or (character == "$" and command[index:index + 2] == "$("):
            return None
        if character in "<>(){}":
            return None
        if character in " \t":
            if not head_word_checked and head_word:
                if not head_word_quoted and "".join(head_word) in _SHELL_CONTROL_RESERVED_WORDS:
                    return None
                head_word_checked = True
            index += 1
            continue
        if character in "\n\r;&|":
            if not head_word_checked and head_word:
                if not head_word_quoted and "".join(head_word) in _SHELL_CONTROL_RESERVED_WORDS:
                    return None
            leaf = command[start:index].strip()
            if not leaf:
                return None
            commands.append(leaf)
            if character in "&|" and index + 1 < len(command) and command[index + 1] == character:
                index += 1
            start = index + 1
            head_word = []
            head_word_quoted = False
            head_word_checked = False
        elif not head_word_checked:
            head_word.append(character)
        index += 1
    if quote is not None or escaped:
        return None
    if (
        not head_word_checked
        and head_word
        and not head_word_quoted
        and "".join(head_word) in _SHELL_CONTROL_RESERVED_WORDS
    ):
        return None
    leaf = command[start:].strip()
    if not leaf:
        return None if commands else []
    commands.append(leaf)
    return commands


def _dynamic_executable(token: str) -> bool:
    """展開後に実行名が変わるwordを検出する。"""
    return bool(re.match(r"^(?:\$[A-Za-z_]|\$\{|\$\(|`)", token))


def _has_active_parameter_expansion(command: str) -> bool:
    """single quote外で一次評価されるparameter expansionを検出する。"""
    quote: str | None = None
    escaped = False
    for character in command:
        if escaped:
            escaped = False
            continue
        if quote == "'":
            if character == "'":
                quote = None
            continue
        if character == "\\":
            escaped = True
            continue
        if character == '"':
            quote = None if quote == '"' else '"'
            continue
        if character == "'" and quote is None:
            quote = "'"
            continue
        if character == "$":
            return True
    return False


def _evaluated_shell_command(tokens: list[str]) -> tuple[bool, str | None]:
    """shellごとのclosed option grammarでcommand-string payloadを返す。"""
    if not tokens:
        return False, None
    if tokens[0] == "eval":
        if len(tokens) < 2:
            return True, None
        return True, " ".join(tokens[1:])
    shell_token = tokens[0]
    shell = Path(shell_token).name if "/" in shell_token else shell_token
    if shell not in _SHELL_EVALUATORS:
        return False, None
    if len(tokens) == 2 and tokens[1] in {"--help", "--version"}:
        return False, None

    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return True, None
        if token.startswith("--"):
            name, separator, attached = token.partition("=")
            if name in _SHELL_UNSUPPORTED_EVALUATING_OPTIONS.get(shell, frozenset()):
                return True, None
            if name in _SHELL_COMMAND_LONG_OPTIONS.get(shell, frozenset()):
                if separator:
                    return True, attached
                if index + 1 >= len(tokens):
                    return True, None
                command = tokens[index + 1]
                if command in {"-c", "--command"} and index + 2 < len(tokens):
                    return True, None
                return True, command
            if name in _SHELL_LONG_NO_ARG_OPTIONS[shell]:
                if separator:
                    return True, None
                index += 1
                continue
            if name in _SHELL_LONG_VALUE_OPTIONS[shell]:
                if separator:
                    if not attached:
                        return True, None
                    index += 1
                    continue
                if index + 1 >= len(tokens):
                    return True, None
                index += 2
                continue
            return True, None
        if token.startswith("+") or not token.startswith("-") or token == "-":
            return True, None
        cluster = token[1:]
        if not cluster or not set(cluster) <= _SHELL_SHORT_OPTIONS[shell] | {"c"}:
            return True, None
        if cluster.count("c") > 1:
            return True, None
        if "c" in cluster:
            if index + 1 >= len(tokens):
                return True, None
            command = tokens[index + 1]
            if command in {"-c", "--command"} and index + 2 < len(tokens):
                return True, None
            return True, command
        index += 1
    return True, None


def _git_shell_evaluating_long_option(option: str) -> bool:
    """Git parse-optionsが受理し得るevaluator long option略記を閉じる。"""
    if not option.startswith("--") or option == "--":
        return False
    return any(candidate.startswith(option) for candidate in _GIT_SHELL_EVALUATING_OPTIONS)


def _trusted_git_executable(token: str) -> bool:
    """PATH経由のbare gitと固定system pathだけをGit grammarへ束縛する。"""
    return token in _TRUSTED_GIT_EXECUTABLES


def _known_safe_git_shape(tokens: list[str]) -> tuple[bool, str | None]:
    """Git builtinと、再分類が必要なbisect run operandを束縛する。"""
    if not tokens or not _trusted_git_executable(tokens[0]):
        return False, None
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if token == "-c" or token.startswith("-c") or token == "--config-env" or token.startswith("--config-env="):
            return False, None
        if token in {"-C", "--git-dir", "--work-tree", "--namespace"}:
            index += 2
            continue
        if token.startswith(("--git-dir=", "--work-tree=", "--namespace=")):
            index += 1
            continue
        if token in {"--no-pager", "--paginate", "--literal-pathspecs", "--no-optional-locks"}:
            index += 1
            continue
        if token.startswith("-"):
            return False, None
        break
    if index >= len(tokens) or tokens[index] not in _SAFE_GIT_BUILTINS:
        return False, None
    subcommand = tokens[index]
    if subcommand == "bisect" and tokens[index + 1:index + 2] == ["run"]:
        if index + 2 >= len(tokens):
            return False, None
        return True, shlex.join(tokens[index + 2:])
    for token in tokens[index + 1:]:
        if token == "--":
            break
        option = token.split("=", 1)[0]
        if _git_shell_evaluating_long_option(option):
            return False, None
        if token.startswith("-") and not token.startswith("--"):
            short_options = _GIT_SHELL_EVALUATING_SHORT_OPTIONS.get(subcommand, frozenset())
            if any(short_option in token[1:] for short_option in short_options):
                return False, None
    return True, None


def _git_environment_allows_shape(
    tokens: list[str],
    assignments: Mapping[str, str],
    *,
    ignore_environment: bool,
) -> bool:
    """環境変更下でchild helper閉包を証明できないGit invocationを一律拒否する。"""
    del tokens
    return not ignore_environment and "PATH" not in assignments


def _known_safe_gh_shape(tokens: list[str]) -> bool:
    if len(tokens) >= 2 and tokens[:2] == ["alias", "list"]:
        return all(token in _SAFE_ALIAS_FLAGS for token in tokens[2:])
    if tokens in (["extension", "list"], ["extension", "list", "--help"]):
        return True
    return False


def _unknown_executable_merge_shape(tokens: list[str]) -> bool:
    if not tokens or tokens[0] in _SAFE_DATA_EXECUTABLES:
        return False
    if tokens[0] == "env":
        executable_index = next(
            (
                index
                for index, token in enumerate(tokens[1:], start=1)
                if not token.startswith("-") and "=" not in token
            ),
            None,
        )
        if executable_index is None:
            return False
        executable = tokens[executable_index]
        if _dynamic_executable(executable):
            return True
        return _unknown_executable_merge_shape(tokens[executable_index:])
    if any("$" in token or "`" in token for token in tokens[1:]):
        return True
    if any(tokens[index:index + 2] == ["pr", "merge"] for index in range(1, len(tokens) - 1)):
        return True
    merge_positions = [index for index, token in enumerate(tokens) if token == "merge"]
    if merge_positions:
        for index in merge_positions:
            tail = tokens[index + 1:]
            if (
                any(re.fullmatch(r"[1-9][0-9]*", token) for token in tail)
                or any(token in {"--merge", "--rebase", "--squash", "--auto"} for token in tail)
                or tokens[0].startswith("$")
                or any("=" in token or token.startswith("$") for token in tokens[:index])
            ):
                return True
    if len(tokens) > 2 and tokens[1] == "api" and any(
        "$" in token or "`" in token for token in tokens[2:]
    ):
        return True
    if len(tokens) > 2 and tokens[1] == "api":
        tail = " ".join(tokens[2:]).casefold()
        return any(marker in tail for marker in ("/pulls/", "graphql", "mergepullrequest", "automerge"))
    return False


def _read_graphql_query_file(
    reference: str, payload: Mapping[str, Any], *, cwd: Path | None,
) -> str:
    if not reference.startswith("@") or reference == "@-":
        raise ValueError("graphql query source")
    raw_path = reference[1:]
    if not raw_path or any(marker in raw_path for marker in ("$", "`", "\0")):
        raise ValueError("graphql query source")
    payload_cwd = payload.get("cwd")
    if not isinstance(payload_cwd, str) or not Path(payload_cwd).is_absolute():
        raise ValueError("graphql cwd")
    try:
        root = Path(payload_cwd).resolve(strict=True)
        hook_root = (Path.cwd() if cwd is None else cwd).resolve(strict=True)
        if root != hook_root:
            raise ValueError("graphql cwd")
        candidate = root / raw_path
        info = candidate.lstat()
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ValueError("graphql query file")
        if info.st_size > _MAX_GRAPHQL_QUERY_BYTES:
            raise ValueError("graphql query file")
        query = resolved.read_text(encoding="utf-8")
        after = resolved.stat()
    except (OSError, RuntimeError, UnicodeDecodeError) as exc:
        raise ValueError("graphql query file") from exc
    if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ) or "\0" in query:
        raise ValueError("graphql query file")
    return query


def _gh_prefix(tokens: list[str]) -> tuple[list[str], str | None]:
    if not tokens or tokens.pop(0) != "gh":
        raise ValueError("gh")
    repository: str | None = None
    while tokens and tokens[0].startswith("-"):
        token = tokens.pop(0)
        if token in {"-R", "--repo"}:
            if not tokens or repository is not None:
                raise ValueError("repo")
            repository = _canonical_repository(tokens.pop(0))
        elif token.startswith("--repo=") and repository is None:
            repository = _canonical_repository(token.split("=", 1)[1])
        else:
            raise ValueError("global flag")
    return tokens, repository


def _cli_operation(
    payload: Mapping[str, Any], tokens: list[str], wrappers: list[str], *, cwd: Path | None,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> PreUseClassification:
    try:
        remaining, repository = _gh_prefix(tokens)
    except ValueError:
        return _error("CLASSIFIER_UNKNOWN", tokens)
    if len(remaining) < 2 or remaining[:2] != ["pr", "merge"]:
        return _error("CLASSIFIER_UNKNOWN", remaining)
    args = remaining[2:]
    if "--auto" in args:
        return _block("AUTO_MERGE_DENIED", args)
    methods: list[str] = []
    pr_number: int | None = None
    title: str | None = None
    message: str | None = None
    expected: str | None = None
    index = 0
    while index < len(args):
        token = args[index]
        if token in {"--merge", "--rebase", "--squash"}:
            methods.append(token[2:])
            index += 1
            continue
        if token in {"--delete-branch"}:
            index += 1
            continue
        value_flags = {
            "--subject": "title", "-s": "title", "--body": "message", "-b": "message",
            "--match-head-commit": "expected", "-R": "repository", "--repo": "repository",
        }
        field = value_flags.get(token)
        if field is not None:
            if index + 1 >= len(args):
                return _error("CLASSIFIER_UNKNOWN", args)
            value = args[index + 1]
            if field == "title" and title is None:
                title = value
            elif field == "message" and message is None:
                message = value
            elif field == "expected" and expected is None and _OID.fullmatch(value):
                expected = value
            elif field == "repository" and repository is None:
                try:
                    repository = _canonical_repository(value)
                except ValueError:
                    return _error("TARGET_AMBIGUOUS", args)
            else:
                return _error("CLASSIFIER_UNKNOWN", args)
            index += 2
            continue
        if token.startswith("--repo=") and repository is None:
            try:
                repository = _canonical_repository(token.split("=", 1)[1])
            except ValueError:
                return _error("TARGET_AMBIGUOUS", args)
            index += 1
            continue
        if token.startswith("-"):
            return _error("CLASSIFIER_UNKNOWN", args)
        if pr_number is not None or not re.fullmatch(r"[1-9][0-9]*", token):
            return _error("TARGET_AMBIGUOUS", args)
        pr_number = int(token)
        index += 1
    if pr_number is None or len(methods) != 1:
        return _error("MERGE_METHOD_UNKNOWN" if pr_number is not None else "TARGET_AMBIGUOUS", args)
    merge_method = cast(Literal["merge", "rebase", "squash"], methods[0])
    if repository is None:
        try:
            repository = repository_from_cwd(payload, cwd=cwd, runner=runner)
        except ValueError:
            return _error("TARGET_AMBIGUOUS", args)
    raw_operation = {
        "repository": repository, "pr_number": pr_number, "merge_method": merge_method,
        "transport": "cli-wrapped" if wrappers else "cli-direct", "wrappers": wrappers,
        "commit_title": title, "commit_message": message, "expected_head_oid": expected,
    }
    operation_fp = fingerprint(raw_operation)
    operation = MergeOperation(
        repository, pr_number, merge_method, raw_operation["transport"], title, message,
        expected, operation_fp,
    )
    return PreUseClassification("merge", "CLASSIFIED", operation, operation_fp)


def _rest_operation(
    payload: Mapping[str, Any], tokens: list[str], wrappers: list[str], *, cwd: Path | None,
) -> PreUseClassification | None:
    try:
        remaining, _ = _gh_prefix(tokens)
    except ValueError:
        return _error("CLASSIFIER_UNKNOWN", tokens)
    if not remaining or remaining.pop(0) != "api":
        return None
    endpoint: str | None = None
    method = "GET"
    fields: dict[str, str] = {}
    typed_fields: set[str] = set()
    index = 0
    while index < len(remaining):
        token = remaining[index]
        if token in {"-X", "--method"} and index + 1 < len(remaining):
            method = remaining[index + 1].upper()
            index += 2
        elif token.startswith("--method="):
            method = token.split("=", 1)[1].upper()
            index += 1
        elif token in {"-f", "--raw-field", "-F", "--field"} and index + 1 < len(remaining):
            raw = remaining[index + 1]
            if "=" not in raw:
                return _error("CLASSIFIER_UNKNOWN", remaining)
            key, value = raw.split("=", 1)
            if key in fields:
                return _error("CLASSIFIER_UNKNOWN", remaining)
            fields[key] = value
            if token in {"-F", "--field"}:
                typed_fields.add(key)
            index += 2
        elif token.startswith("-"):
            return _error("CLASSIFIER_UNKNOWN", remaining)
        elif endpoint is None:
            endpoint = token
            index += 1
        else:
            return _error("CLASSIFIER_UNKNOWN", remaining)
    query = fields.get("query", "")
    if endpoint == "graphql" and "query" in typed_fields and query.startswith("@"):
        try:
            file_query = _read_graphql_query_file(query, payload, cwd=cwd)
        except ValueError:
            return _error("CLASSIFIER_UNKNOWN", remaining)
        if "enablePullRequestAutoMerge" in file_query:
            return _block("AUTO_MERGE_DENIED", remaining)
        return _error("CLASSIFIER_UNKNOWN", remaining)
    if endpoint == "graphql" and re.fullmatch(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?", query):
        return _error("CLASSIFIER_UNKNOWN", remaining)
    if "enablePullRequestAutoMerge" in query:
        return _block("AUTO_MERGE_DENIED", remaining)
    if "mergePullRequest" in query:
        return _error("CLASSIFIER_UNKNOWN", remaining)
    if endpoint is None:
        return None
    match = _REST_MERGE.fullmatch(endpoint)
    if match is None:
        return _error("CLASSIFIER_UNKNOWN", remaining) if "merge" in endpoint.casefold() else None
    if method != "PUT":
        return _error("CLASSIFIER_UNKNOWN", remaining)
    if set(fields) - {"merge_method", "commit_title", "commit_message", "sha"}:
        return _error("CLASSIFIER_UNKNOWN", remaining)
    merge_method = fields.get("merge_method")
    if merge_method not in {"merge", "rebase", "squash"}:
        return _error("MERGE_METHOD_UNKNOWN", remaining)
    merge_method = cast(Literal["merge", "rebase", "squash"], merge_method)
    expected = fields.get("sha")
    if expected is not None and not _OID.fullmatch(expected):
        return _error("IDENTITY_MISMATCH", remaining)
    repository = f"{match.group(1)}/{match.group(2)}"
    raw_operation = {
        "repository": repository, "pr_number": int(match.group(3)),
        "merge_method": merge_method, "transport": "rest", "wrappers": wrappers,
        "commit_title": fields.get("commit_title"),
        "commit_message": fields.get("commit_message"), "expected_head_oid": expected,
    }
    operation_fp = fingerprint(raw_operation)
    operation = MergeOperation(
        repository, int(match.group(3)), merge_method, "rest",
        fields.get("commit_title"), fields.get("commit_message"), expected, operation_fp,
    )
    return PreUseClassification("merge", "CLASSIFIED", operation, operation_fp)


def _connector_operation(tool_name: str, tool_input: Mapping[str, Any]) -> PreUseClassification:
    if tool_name in _CONNECTOR_AUTO:
        return _block("AUTO_MERGE_DENIED", {"tool_name": tool_name, "tool_input": tool_input})
    expected_keys = {
        "repository_full_name", "pr_number", "merge_method", "commit_title",
        "commit_message", "expected_head_sha",
    }
    if set(tool_input) - expected_keys:
        return _error("CLASSIFIER_UNKNOWN", tool_input)
    repository = tool_input.get("repository_full_name")
    number = tool_input.get("pr_number")
    method = tool_input.get("merge_method")
    title = tool_input.get("commit_title")
    message = tool_input.get("commit_message")
    expected = tool_input.get("expected_head_sha")
    try:
        repository = _canonical_repository(repository) if isinstance(repository, str) else ""
    except ValueError:
        repository = ""
    if not repository or isinstance(number, bool) or not isinstance(number, int) or number < 1:
        return _error("TARGET_AMBIGUOUS", tool_input)
    if method not in {"merge", "rebase", "squash"}:
        return _error("MERGE_METHOD_UNKNOWN", tool_input)
    if title is not None and not isinstance(title, str) or message is not None and not isinstance(message, str):
        return _error("MERGE_OVERRIDE_AMBIGUOUS", tool_input)
    if expected is not None and (not isinstance(expected, str) or not _OID.fullmatch(expected)):
        return _error("IDENTITY_MISMATCH", tool_input)
    raw_operation = {
        "repository": repository, "pr_number": number, "merge_method": method,
        "transport": "connector", "commit_title": title, "commit_message": message,
        "expected_head_oid": expected,
    }
    operation_fp = fingerprint(raw_operation)
    operation = MergeOperation(
        repository, number, method, "connector", title, message, expected, operation_fp
    )
    return PreUseClassification("merge", "CLASSIFIED", operation, operation_fp)


def classify_pre_use(
    payload: Mapping[str, Any],
    *,
    cwd: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    _depth: int = 0,
) -> PreUseClassification | None:
    """Codex/Claude PreToolUse payloadを分類し、非mergeだけNoneで通過させる。"""
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        return _error("CLASSIFIER_UNKNOWN", payload)
    if tool_name in _CONNECTOR_MERGE | _CONNECTOR_AUTO:
        return _connector_operation(tool_name, tool_input)
    if "merge" in tool_name.casefold() and tool_name.startswith(("mcp__", "github_")):
        return _error("CLASSIFIER_UNKNOWN", {"tool_name": tool_name})
    if tool_name not in {"Bash", "bash"}:
        return None
    command = tool_input.get("command")
    if not isinstance(command, str):
        return _error("CLASSIFIER_UNKNOWN", tool_input)
    if _depth >= 8:
        return _error("CLASSIFIER_UNKNOWN", command)
    shell_commands = _split_shell_commands(command)
    if shell_commands is None:
        return _error("CLASSIFIER_UNKNOWN", command)
    if len(shell_commands) > 1:
        for leaf in shell_commands:
            if _compound_changes_shell_state(leaf):
                return _error("CLASSIFIER_UNKNOWN", command)
            classified = classify_pre_use(
                {"tool_name": "Bash", "tool_input": {"command": leaf}},
                cwd=cwd,
                runner=runner,
                _depth=_depth + 1,
            )
            if classified is not None:
                return _error("CLASSIFIER_UNKNOWN", command)
        return None
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return _error("CLASSIFIER_UNKNOWN", command)
    environment = _command_environment(tokens)
    if environment is None:
        return _error("CLASSIFIER_UNKNOWN", command)
    remaining, wrappers, assignments, ignore_environment = environment
    if not remaining:
        return None
    if not _environment_allows_executable(
        assignments,
        ignore_environment=ignore_environment,
        executable=remaining[0],
    ):
        return _error("CLASSIFIER_UNKNOWN", command)
    if remaining[0] in _SHELL_STATE_COMMANDS:
        return _error("CLASSIFIER_UNKNOWN", command)
    if remaining[0] != "gh":
        if _dynamic_executable(remaining[0]):
            return _error("CLASSIFIER_UNKNOWN", command)
        if remaining[0] == "eval" and _has_active_parameter_expansion(command):
            return _error("CLASSIFIER_UNKNOWN", command)
        evaluator, evaluated_command = _evaluated_shell_command(remaining)
        if evaluator:
            if evaluated_command is None:
                return _error("CLASSIFIER_UNKNOWN", command)
            nested = classify_pre_use(
                {"tool_name": "Bash", "tool_input": {"command": evaluated_command}},
                cwd=cwd,
                runner=runner,
                _depth=_depth + 1,
            )
            if nested is not None:
                if nested.kind == "block":
                    return _block(nested.reason, command)
                return _error("CLASSIFIER_UNKNOWN", command)
            return None
        executable_basename = Path(remaining[0]).name
        if "/" in remaining[0] and any(shell in executable_basename for shell in _SHELL_EVALUATORS):
            return _error("CLASSIFIER_UNKNOWN", command)
        if remaining[0] in _SAFE_DATA_EXECUTABLES:
            if not _state_independent_data_shape(remaining):
                return _error("CLASSIFIER_UNKNOWN", command)
            return None
        if executable_basename == "git":
            known_safe, evaluated_command = _known_safe_git_shape(remaining)
            if not known_safe:
                return _error("CLASSIFIER_UNKNOWN", command)
            if not _git_environment_allows_shape(
                remaining,
                assignments,
                ignore_environment=ignore_environment,
            ):
                return _error("CLASSIFIER_UNKNOWN", command)
            if evaluated_command is None:
                return None
            nested = classify_pre_use(
                {"tool_name": "Bash", "tool_input": {"command": evaluated_command}},
                cwd=cwd,
                runner=runner,
                _depth=_depth + 1,
            )
            if nested is not None:
                return _error("CLASSIFIER_UNKNOWN", command)
            return None
        if "gh" in remaining or _unknown_executable_merge_shape(remaining):
            return _error("CLASSIFIER_UNKNOWN", command)
        return None
    if remaining in (["gh", "--version"], ["gh", "--help"], ["gh", "help"], ["gh", "version"]):
        return None
    try:
        subcommand, _ = _gh_prefix(list(remaining))
    except ValueError:
        return _error("CLASSIFIER_UNKNOWN", remaining)
    if not subcommand:
        return None
    if subcommand[0] == "api" and _has_active_parameter_expansion(command):
        return _error("CLASSIFIER_UNKNOWN", command)
    if _known_safe_gh_shape(subcommand):
        return None
    is_merge_candidate = (
        subcommand[0] == "api"
        or subcommand[:2] == ["pr", "merge"]
        or subcommand[0] not in _GH_NON_MERGE_COMMANDS | {"pr"}
        or subcommand[0] == "pr" and (len(subcommand) < 2 or subcommand[1] not in _GH_NON_MERGE_PR_COMMANDS)
    )
    if not is_merge_candidate:
        return None
    rest = _rest_operation(payload, list(remaining), wrappers, cwd=cwd)
    if rest is not None:
        return rest
    if subcommand[0] == "api":
        return None
    if subcommand[:2] != ["pr", "merge"]:
        return _error("CLASSIFIER_UNKNOWN", remaining)
    return _cli_operation(payload, list(remaining), wrappers, cwd=cwd, runner=runner)
