"""100 物理行を超える Python モジュールのラチェット検査。"""

from pathlib import Path

from .model import Finding


RULE = "module-over-100-lines"
MAX_LINES = 100


def inspect_module_length(
    root: Path,
    path: Path,
    baseline_lines: dict[str, int],
) -> tuple[list[Finding], dict[str, int]]:
    relative = path.relative_to(root).as_posix()
    line_count = len(path.read_text(encoding="utf-8").splitlines())
    if line_count <= MAX_LINES:
        return [], {}
    status = "accepted-debt" if baseline_lines.get(relative) == line_count else "violation"
    detail = (
        f"{line_count} physical lines; split responsibilities to <= {MAX_LINES} lines"
        if status == "violation"
        else f"existing debt fixed at {line_count} lines; any size change requires re-baselining"
    )
    finding = Finding(RULE, relative, 1, status, detail, relative)
    return [finding], {relative: line_count}
