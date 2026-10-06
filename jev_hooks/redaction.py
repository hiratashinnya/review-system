"""Remove declared secrets and common credential forms without environment dumps."""
import os
import re

REDACTED = "[REDACTED]"
SENSITIVE_KEY = re.compile(
    r"token|password|passwd|secret|authorization|credential|private.?key|api.?key|cookie",
    re.I,
)
PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)",
    re.S,
)
CREDENTIAL = re.compile(
    r'''(?i)(\b(?:[\w-]*(?:token|password|passwd|secret|api[_-]?key|private[_-]?key)|authorization|cookie)\b["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,;]+)''',
)
BEARER = re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
TOKEN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)\b")


def known_secrets(config, authorization_key=""):
    names = ["TYPESAFE_API_KEY", *config.get("secret_env_vars", [])]
    return tuple(sorted({authorization_key, *(os.environ.get(name, "") for name in names)}
                        - {""}, key=len, reverse=True))


def redact_text(value, secrets):
    for secret in secrets:
        value = value.replace(secret, REDACTED)
    value = PRIVATE_KEY.sub(REDACTED, value)
    value = BEARER.sub(REDACTED, value)
    value = CREDENTIAL.sub(lambda match: match[1] + REDACTED, value)
    return TOKEN.sub(REDACTED, value)


def redact(value, secrets):
    if isinstance(value, str):
        return redact_text(value, secrets)
    if isinstance(value, dict):
        return {key: REDACTED if SENSITIVE_KEY.search(str(key)) else redact(item, secrets)
                for key, item in value.items() if isinstance(key, str)
                and key not in {"thinking", "reasoning", "signature", "data"}}
    if isinstance(value, (list, tuple)):
        return [redact(item, secrets) for item in value]
    if value is None or type(value) in (bool, int, float):
        return value
    return None
