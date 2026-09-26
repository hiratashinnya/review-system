"""4 行以上の連続した行コメントを検出する。"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
import tokenize

from .model import Finding


RULE = "comment-over-3-lines"
MAX_COMMENT_LINES = 3


def _full_line_comments(text: str) -> list[tuple[int, str]]:
    lines = text.splitlines()
    comments: list[tuple[int, str]] = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type != tokenize.COMMENT:
            continue
        prefix = lines[token.start[0] - 1][: token.start[1]]
        if not prefix.strip():
            comments.append((token.start[0], token.string))
    return comments


def _long_comment_blocks(text: str) -> list[list[tuple[int, str]]]:
    blocks: list[list[tuple[int, str]]] = []
    for line_number, comment in _full_line_comments(text):
        if not blocks or line_number != blocks[-1][-1][0] + 1:
            blocks.append([])
        blocks[-1].append((line_number, comment))
    return [block for block in blocks if len(block) > MAX_COMMENT_LINES]


def _block_digest(block: list[tuple[int, str]]) -> str:
    body = "\n".join(comment for _, comment in block).encode("utf-8")
    return hashlib.sha256(body).hexdigest()[:16]


def inspect_comment_blocks(
    root: Path,
    path: Path,
    baseline_blocks: dict[str, int],
) -> tuple[list[Finding], dict[str, int]]:
    relative = path.relative_to(root).as_posix()
    actual: dict[str, int] = {}
    findings: list[Finding] = []
    for block in _long_comment_blocks(path.read_text(encoding="utf-8")):
        key = f"{relative}|{_block_digest(block)}"
        actual[key] = actual.get(key, 0) + 1
        status = "accepted-debt" if actual[key] <= baseline_blocks.get(key, 0) else "violation"
        detail = f"{len(block)} consecutive comment lines; move rationale to durable documentation"
        findings.append(Finding(RULE, relative, block[0][0], status, detail, key))
    return findings, actual
