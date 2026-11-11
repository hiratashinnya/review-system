"""カルテ文書の解析。移設した設計理由は .ai/rationale/karte-module-split.md を参照。"""

from __future__ import annotations

from .block_parser import parse_blocks
from .block_records import _attempt_from_block, _finding_from_block, _result_from_block
from .format_error import KarteFormatError
from .int_args import matched_int
from .karte_record import Karte
from .vocabulary import ATTEMPT_TITLE_RE, DOC_HEADER_RE, RESULT_TITLE_RE, SECTION_ATTEMPTS, SECTION_FINDINGS


def parse(text: str) -> Karte:
    """カルテ文書全体をパースする。書式違反は :class:`KarteFormatError`。"""
    issue = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        matched = DOC_HEADER_RE.match(line)
        if matched:
            issue = matched_int(matched.group(1), KarteFormatError, "カルテ見出しの issue")
        break
    if issue is None:
        raise KarteFormatError("先頭行が '# Karte: issue-<N>' でない（カルテ書式ではない）")

    karte = Karte(issue=issue)
    for block in parse_blocks(text):
        if block.section == SECTION_FINDINGS:
            karte.findings.append(_finding_from_block(block, issue))
        elif block.section == SECTION_ATTEMPTS:
            if attempt_title := ATTEMPT_TITLE_RE.match(block.title):
                karte.attempts.append(_attempt_from_block(block, attempt_title))
            elif result_title := RESULT_TITLE_RE.match(block.title):
                karte.results.append(_result_from_block(block, result_title))
            else:
                raise KarteFormatError(
                    f"{block.lineno} 行目: '## {SECTION_ATTEMPTS}' 配下の見出しは "
                    f"'Attempt <k>' か 'Result <k>' のみ: {block.title!r}"
                )
        else:
            raise KarteFormatError(
                f"{block.lineno} 行目: 未知のセクション {block.section!r} 配下のブロック "
                f"{block.title!r}（許可されるのは '{SECTION_FINDINGS}' と '{SECTION_ATTEMPTS}'）"
            )

    seen = set()
    for item in karte.findings:
        if item.id in seen:
            raise KarteFormatError(f"finding ID が台帳内で重複している: {item.id}")
        seen.add(item.id)
    numbers = set()
    for item in karte.attempts:
        if item.number in numbers:
            raise KarteFormatError(f"Attempt 番号が重複している: {item.number}")
        numbers.add(item.number)
    for item in karte.results:
        if item.attempt not in numbers:
            raise KarteFormatError(f"Result が指す Attempt が存在しない: {item.attempt}")
    karte.findings.sort(key=lambda item: item.seq)
    karte.attempts.sort(key=lambda item: item.number)
    return karte
