"""Windows読取専用応答をclosed schemaへ変換し、入力bindingへ結合する。"""

from .cohort_fields import BINDING_ENUMS
from .cohort_schema import validated_files
from .cohort_validation import checked_hash, exact_object
from .native_paths import os_binding, text_sha256, wsl_user_binding
from .request_policy import request_path_binding
from .types import Request

REPLY_FIELDS = {"ok", "nonce", "windows_os_sha256", "windows_principal_sha256",
                "executable_sha256", "files", "admin_gateway_candidate_absent",
                "gateway_environment_present", "update_disabled_for_child", "os_cwd_observed",
                "settings_writes", "agy_launches"}


def validated_windows_reply(value: object, nonce: str) -> dict:
    """raw message/pathを返さず、nonceと値型・作用0を検査する。"""
    try:
        reply = exact_object(value, REPLY_FIELDS)
        if reply["ok"] is not True or reply["nonce"] != nonce:
            raise ValueError("cohort_windows_reply_invalid")
        for name in ("windows_os_sha256", "windows_principal_sha256", "executable_sha256"):
            checked_hash(reply[name])
        validated_files(reply["files"])
        for name, expected in (("admin_gateway_candidate_absent", True),
                               ("gateway_environment_present", False),
                               ("update_disabled_for_child", True), ("os_cwd_observed", False)):
            if type(reply[name]) is not bool or reply[name] is not expected:
                raise ValueError("cohort_windows_reply_invalid")
        if any(type(reply[name]) is not int or reply[name] != 0
               for name in ("settings_writes", "agy_launches")):
            raise ValueError("cohort_windows_reply_invalid")
    except (ValueError, KeyError, TypeError):
        raise ValueError("cohort_windows_reply_invalid") from None
    return reply


def current_binding_values(request: Request, reply: dict) -> dict:
    """native欄は要求path射影であり、OS cwdを新たに観測したとは宣言しない。"""
    return {"os_sha256": os_binding(reply["windows_os_sha256"]),
            "user_home_sha256": wsl_user_binding(reply["windows_principal_sha256"]),
            **request_path_binding(request),
            "executable_path_sha256": text_sha256(str(request.executable.resolve(strict=True))),
            "executable_sha256": reply["executable_sha256"], **BINDING_ENUMS}
