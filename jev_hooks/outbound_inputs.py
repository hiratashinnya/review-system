"""Project tool arguments without file bodies or shell argument values."""
import json
import re
import shlex
from .redaction import redact, redact_text

SENSITIVE_FILE = re.compile(
    r"(?i)(?:^|[/\\\s'\"])(?:\.env(?:\.[\w-]+)?|\.envrc|\.ssh|\.aws|\.kube|\.npmrc|\.pypirc|\.netrc|\.git-credentials|"
    r"id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?|terraform\.tfstate|"
    r"credentials(?:\.[\w-]+)?|[^/\\\s'\"]*(?:secret|private[_-]?key)[^/\\\s'\"]*|"
    r"[^/\\\s'\"]+\.(?:pem|key|p12|pfx))(?:$|[/\\\s'\"])"
)
INPUT_FIELDS = {"questions", "query", "pattern", "url", "file_path", "path", "glob"}
GIT_VERBS = {"push", "pull", "fetch", "merge", "commit", "checkout", "status", "diff",
             "log", "reset", "add", "rebase", "tag", "switch", "restore", "clean", "show"}


def sensitive_input(inputs):
    if not isinstance(inputs, dict):
        return True
    targets = {key: value for key, value in inputs.items()
               if key in {"file_path", "path", "filename", "file", "target", "uri", "command"}}
    return bool(SENSITIVE_FILE.search(json.dumps(targets, ensure_ascii=False)))


def shell_tool(name):
    return any(word in name.lower() for word in ("bash", "shell", "exec", "terminal"))


def command_intent(command, secrets):
    if not isinstance(command, str):
        return "[OMITTED]"
    heredoc = "<<" in command
    command = command.split("<<", 1)[0]
    try:
        lexer = shlex.shlex(command.replace("\n", ";"), posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split, lexer.commenters = True, ""
        tokens = list(lexer)
    except ValueError:
        return "[OMITTED: unparsed shell command]"
    projected, executable = [], None
    for token in tokens:
        if token and all(char in ";&|()" for char in token):
            projected.append(token)
            executable = None
        elif executable is None:
            if "=" in token:
                continue
            executable = token.rsplit("/", 1)[-1]
            projected.append(executable if re.fullmatch(r"[A-Za-z_][\w.-]*", executable) else "[OMITTED]")
        elif executable == "git" and token in GIT_VERBS:
            projected.append(token)
        elif re.fullmatch(r"--?[A-Za-z][\w-]*(?:=.*)?", token):
            projected.append(token.split("=", 1)[0])
        else:
            projected.append("[ARGUMENT OMITTED]")
    if heredoc:
        projected.append("[HEREDOC OMITTED]")
    return redact_text(" ".join(projected), secrets)


def project_input(inputs, secrets, name=""):
    if not isinstance(inputs, dict):
        return "[OMITTED]"
    if shell_tool(name) or "command" in inputs:
        return {"command": command_intent(inputs.get("command"), secrets)}
    if sensitive_input(inputs):
        return "[OMITTED: sensitive file input]"
    return {key: redact(value, secrets) for key, value in inputs.items() if key in INPUT_FIELDS}
