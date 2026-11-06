#!/usr/bin/env python3
"""agy-delegate 起動時に必読資料を注入する。"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agy_delegate.reference import reference_context  # noqa: E402


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if payload.get("agent_type") != "agy-delegate":
            return 0
        print(reference_context(ROOT), end="")
    except (OSError, UnicodeError, ValueError, AttributeError) as error:
        print(f"必読資料の注入に失敗しました。inspect/run を行わず停止してください: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
