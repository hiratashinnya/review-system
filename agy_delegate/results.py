"""agy 固有失敗信号を全件保持する（JSON型は agy 1.3.3 実測契約）。"""

import re

from .output_contract import contract_reasons, validated_usage
from .strict_json import load_json
from .types import Result

ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")


KNOWN_STATUSES = {"SUCCESS", "ERROR"}  # agy 1.3.3 実測で観測した status のみ公開する。


def valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(ID_PATTERN.fullmatch(value))


def public_status(value: str | None) -> str | None:
    """既知値だけを CLI stdout へ出す。生値は当該実行の result.json にだけ残る。"""
    return value if value is None or value in KNOWN_STATUSES else "[redacted: unrecognized status]"


def public_identifier(value: str | None) -> str | None:
    """形式が妥当な会話 ID だけを CLI stdout へ出す。不正な生値は公開しない。"""
    return value if value is None or valid_id(value) else "[redacted: invalid id]"


def normalize(run_id: str, stdout: str, stderr: str, code: int) -> Result:
    """構造契約成功は意味的完了を保証しない。欠落値を成功へ補完しない。"""
    result = Result(run_id, agy_exit_code=code)
    text = stderr.casefold()
    result.stderr_length = len(stderr)
    for marker, reason in (("print timeout", "print_timeout"),
                           ("no output produced", "no_output"), ("error:", "stderr_error")):
        if marker in text:
            result.reasons.append(reason)
    result.truncated = "print_timeout" in result.reasons
    if text.strip() and not result.reasons:
        result.reasons.append("stderr_unrecognized")
    if code != 0:
        result.reasons.append("nonzero_exit")
    try:
        data = load_json(stdout)
    except ValueError:
        data = None
    if not isinstance(data, dict):
        result.reasons.append("json_invalid")
    else:
        _inspect_fields(data, result)
    result.classification = "failed" if result.reasons else "success_candidate"
    if any(reason.startswith("d0_") for reason in result.reasons):
        result.classification = "denied"
    return result


def _inspect_fields(data: dict, result: Result) -> None:
    result.reasons.extend(contract_reasons(data))
    result.usage = validated_usage(data.get("usage"))
    for name in ("status", "conversation_id", "response", "error"):
        if isinstance(data.get(name), str):
            setattr(result, name, data[name])
    if isinstance(data.get("denied_actions"), list):
        result.denied_actions = data["denied_actions"]
    if "error" in data:
        result.reasons.append("agy_error_present")
    if result.status != "SUCCESS":
        result.reasons.append("status_not_success")
    if result.denied_actions:
        result.reasons.append("d0_denied_actions")
    if not valid_id(result.conversation_id):
        result.reasons.append("conversation_id_invalid")
