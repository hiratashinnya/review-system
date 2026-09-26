"""データクラスと具体ロジッククラスのファイル分離を検査する。"""

from pathlib import Path

from .class_roles import classify_top_level_classes
from .content_fingerprint import content_sha256
from .model import Finding


RULE = "data-and-logic-class-cohabitation"


def inspect_class_separation(
    root: Path,
    path: Path,
    baseline_mixed: dict[str, dict[str, object]],
) -> tuple[list[Finding], dict[str, dict[str, object]]]:
    data_classes, logic_classes = classify_top_level_classes(path)
    if not data_classes or not logic_classes:
        return [], {}
    relative = path.relative_to(root).as_posix()
    fingerprint: dict[str, object] = {
        "data": sorted(node.name for node in data_classes),
        "logic": sorted(node.name for node in logic_classes),
        "sha256": content_sha256(path.read_text(encoding="utf-8")),
    }
    status = (
        "accepted-debt"
        if baseline_mixed.get(relative) == fingerprint
        else "violation"
    )
    detail = (
        f"data={fingerprint['data']} logic={fingerprint['logic']}; "
        "place data and behavior in separate files"
    )
    line = min(node.lineno for node in data_classes + logic_classes)
    finding = Finding(RULE, relative, line, status, detail, relative)
    return [finding], {relative: fingerprint}
