"""Explicit standalone configuration, unrelated to Claude settings."""
import json
from pathlib import Path

DEFAULTS = {
    "mode": "shadow", "evaluator": "mock", "model": "jev-1.13.0",
    "confidence_threshold": 0.9, "timeout_seconds": 8, "retries": 1,
    "max_blocks_per_rule": 2, "research_tools": [],
    "question_tool_available": True, "skill_definitions": [],
    "state_dir": "~/.local/state/jev-hooks", "rule_version": "1.0",
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
    return config
