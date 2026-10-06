"""Explicit standalone configuration, unrelated to Claude settings."""
import json
from pathlib import Path
from .policy import RULE_VERSION

DEFAULTS = {
    "mode": "shadow", "evaluator": "mock", "model": "jev-1.13.0",
    "confidence_threshold": 0.9, "timeout_seconds": 8, "retries": 1,
    "max_blocks_per_rule": 2, "research_tools": [],
    "question_tool_available": True, "skill_definitions": [],
    "secret_env_vars": [], "api_key_env": "TYPESAFE_API_KEY", "audit_retention": 10000,
    "state_dir": "~/.local/state/jev-hooks", "rule_version": RULE_VERSION,
}


def load_config(path=None):
    config = dict(DEFAULTS)
    if path:
        config.update(json.loads(Path(path).read_text()))
    if config["mode"] not in {"shadow", "enforce"}:
        raise ValueError("mode must be shadow or enforce")
    if not 0 <= config["confidence_threshold"] <= 1:
        raise ValueError("threshold outside [0,1]")
    if not 1 <= config["max_blocks_per_rule"] <= 10:
        raise ValueError("invalid block budget")
    names = config["secret_env_vars"]
    if not isinstance(names, list) or any(not isinstance(name, str) or not name for name in names) or len(names) != len(set(names)):
        raise ValueError("invalid secret environment names")
    if type(config["audit_retention"]) is not int or not 1 <= config["audit_retention"] <= 100000:
        raise ValueError("invalid audit retention")
    return config
