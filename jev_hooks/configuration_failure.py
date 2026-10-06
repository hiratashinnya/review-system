"""Distinguish required credentials from uncertain semantic evaluations."""
import os


class ConfigurationFault(RuntimeError):
    code = "missing_api_key"


def api_key(config):
    name = config.get("api_key_env", "TYPESAFE_API_KEY")
    if not isinstance(name, str) or not name.strip():
        raise ConfigurationFault("missing_api_key")
    value = os.environ.get(name, "")
    if not value.strip():
        raise ConfigurationFault("missing_api_key")
    return value


def fault_decision(event, config):
    reason = "Jev の必須 API キーが未設定です。設定を修復してから再実行してください。"
    if not isinstance(event, dict) or config.get("mode") != "enforce":
        return {}
    if event.get("hook_event_name") == "Stop":
        return {"decision": "block", "reason": reason}
    if event.get("hook_event_name") == "PreToolUse":
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                "permissionDecision": "deny", "permissionDecisionReason": reason}}
    return {}


def configuration_failure(event, config):
    if config.get("evaluator", "mock") != "jev":
        return {}, None
    try:
        api_key(config)
    except ConfigurationFault:
        return fault_decision(event, config), ConfigurationFault.code
    return {}, None
