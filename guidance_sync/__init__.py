"""PF 常駐 guidance の決定的な生成・整合性検査。"""

from .sync import (
    COMMON_SOURCE,
    PRINCIPLES_SOURCE,
    TARGETS,
    check,
    render,
    rendered_bytes,
    staged_check,
)

__all__ = [
    "COMMON_SOURCE",
    "PRINCIPLES_SOURCE",
    "TARGETS",
    "check",
    "render",
    "rendered_bytes",
    "staged_check",
]
