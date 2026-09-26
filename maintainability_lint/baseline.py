"""Issue #539 時点の既存負債 baseline を厳密に読み込む。"""

from __future__ import annotations

import json
from pathlib import Path


BASELINE_PATH = Path(__file__).with_name("baseline.json")
EXPECTED_KEYS = {
    "schema_version",
    "source",
    "module_lines",
    "comment_blocks",
    "mixed_class_files",
}


class BaselineError(ValueError):
    pass


def load_baseline(path: Path = BASELINE_PATH) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"cannot read baseline {path}: {exc}") from exc
    if not isinstance(data, dict) or set(data) != EXPECTED_KEYS:
        raise BaselineError(f"baseline keys must be exactly {sorted(EXPECTED_KEYS)}")
    if data["schema_version"] != 1:
        raise BaselineError("unsupported baseline schema_version")
    for key in ("module_lines", "comment_blocks", "mixed_class_files"):
        if not isinstance(data[key], dict):
            raise BaselineError(f"baseline {key} must be an object")
    return data
