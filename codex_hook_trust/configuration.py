"""Read hook definitions from a repository's Codex configuration."""

from __future__ import annotations

import json
from pathlib import Path


def count_defined_handlers(repo: Path) -> int:
    """Count handlers registered under every event and matcher group."""
    config_path = repo / ".codex" / "hooks.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"hooks.json を読み込めません: {config_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"hooks.json が不正な JSON です: {config_path}") from error

    events = config.get("hooks") if isinstance(config, dict) else None
    if not isinstance(events, dict):
        raise ValueError(f"hooks.json に hooks オブジェクトがありません: {config_path}")

    count = 0
    for groups in events.values():
        if not isinstance(groups, list):
            raise ValueError(f"hooks.json のイベント定義が不正です: {config_path}")
        for group in groups:
            handlers = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(handlers, list):
                raise ValueError(f"hooks.json の matcher 定義が不正です: {config_path}")
            count += len(handlers)
    return count
