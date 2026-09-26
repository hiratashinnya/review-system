"""100 物理行を超える Python モジュールのラチェット検査。"""

from pathlib import Path

from .content_fingerprint import content_sha256
from .model import Finding


RULE = "module-over-100-lines"
MAX_LINES = 100


def inspect_module_length(
    root: Path,
    path: Path,
    baseline_modules: dict[str, dict[str, object]],
) -> tuple[list[Finding], dict[str, dict[str, object]]]:
    relative = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    line_count = len(text.splitlines())
    if line_count <= MAX_LINES:
        return [], {}
    fingerprint = {"line_count": line_count, "sha256": content_sha256(text)}
    status = (
        "accepted-debt"
        if baseline_modules.get(relative) == fingerprint
        else "violation"
    )
    detail = (
        f"{line_count} physical lines; split responsibilities to <= {MAX_LINES} lines"
        if status == "violation"
        else f"existing debt fixed at {line_count} lines and exact content fingerprint"
    )
    finding = Finding(RULE, relative, 1, status, detail, relative)
    return [finding], {relative: fingerprint}
