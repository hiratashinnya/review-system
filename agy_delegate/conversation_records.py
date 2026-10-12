"""保存済み正規化記録の型と継続可能条件を検査する。"""

from .results import valid_id

RECORD_TYPES = {
    "run_id": str, "classification": str, "reasons": list,
    "agy_exit_code": (int, type(None)), "status": (str, type(None)),
    "conversation_id": (str, type(None)), "response": (str, type(None)),
    "error": (str, type(None)), "denied_actions": list, "truncated": bool, "artifacts": list,
    "completed": bool, "workspace": str,
}


def validate_record(data: object, workspace: str, conversation: str) -> None:
    if not isinstance(data, dict) or set(data) != set(RECORD_TYPES):
        raise ValueError("conversation_record_missing_or_invalid")
    if any(not isinstance(data[name], kind) for name, kind in RECORD_TYPES.items()):
        raise ValueError("conversation_record_missing_or_invalid")
    if not _valid_record_values(data):
        raise ValueError("conversation_record_missing_or_invalid")
    if data["workspace"] != workspace:
        raise ValueError("conversation_workspace_mismatch")
    if (data["classification"] != "success_candidate" or data["status"] != "SUCCESS"
            or data["agy_exit_code"] != 0 or data["denied_actions"] or data["reasons"]
            or data["truncated"] or data["error"] is not None or not isinstance(data["response"], str)):
        raise ValueError("conversation_previous_failure")
    if data["conversation_id"] != conversation:
        raise ValueError("conversation_record_identity_mismatch")


def _valid_record_values(data: dict) -> bool:
    return (valid_id(data["run_id"]) and not isinstance(data["agy_exit_code"], bool)
            and data["classification"] in {"success_candidate", "failed", "denied", "preflight_failed"}
            and all(isinstance(value, str) for value in data["reasons"] + data["artifacts"]))
