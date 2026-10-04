"""Hash declared project inputs; no source text is persisted."""
import hashlib
import json
from .verification import PREFIX
from pathlib import Path


def fingerprint(root, patterns):
    digest = hashlib.sha256()
    for pattern in patterns:
        for path in sorted(Path(root).glob(pattern)):
            if path.is_file():
                digest.update(str(path.relative_to(root)).encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()


def matches(operation, name, inputs):
    return operation.get("tool") == name and all(
        inputs.get(key) == value for key, value in operation.get("input", {}).items())


def successful(result):
    if result.get("is_error") or result.get("error"):
        return False
    content = result.get("content")
    if not isinstance(content, dict) or content.get("interrupted") or content.get("is_error"):
        return False
    if "exit_code" in content:
        return type(content["exit_code"]) is int and content["exit_code"] == 0
    lines = content.get("stdout", "").splitlines()
    try:
        receipt = json.loads(lines[-1][len(PREFIX):]) if lines and lines[-1].startswith(PREFIX) else {}
        return type(receipt.get("exit_code")) is int and receipt["exit_code"] == 0
    except (ValueError, TypeError):
        return False
