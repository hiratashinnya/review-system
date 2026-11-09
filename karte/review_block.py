"""レビューレポートの 1 ブロックを :class:`ReviewFinding` へ読み替える（任意キーの検証を含む）。"""

from .block_fields import require_enum, require_nonempty
from .block_parser import Block
from .disposition import parse_disposition
from .finding_id import parse_finding_id
from .format_error import KarteFormatError
from .harm_detail_lint import check_harm_detail
from .review_finding import ReviewFinding
from .value_codec import check_list, normalize_locus
from .vocabulary import FINDING_STATUSES, HARM_LEVELS, NEW_FINDING_TITLES, SCOPES, SEVERITIES

DISTINCT_FROM_KEY = "distinct_from"


def optional_status(block: Block) -> str:
    """任意キー ``status``（既定 ``open``）。綴り違いは既定へ倒さず fail-close（K-06）。"""
    if "status" not in block.fields:
        return "open"
    return require_enum(block, "status", FINDING_STATUSES)


def parse_distinct_from(block: Block, issue: int) -> tuple:
    """任意キー ``distinct_from``（再発番判定のペア限定エスケープハッチ・K-05）を読む。

    スカラ・リストの両方を受ける。形式違反・対象 issue 違いはここで拒否し、
    台帳に実在するかは台帳を持つ CLI 側で検査する。
    """
    raw = block.fields.get(DISTINCT_FROM_KEY, [])
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    ids = check_list(raw, DISTINCT_FROM_KEY)
    for item in ids:
        issue_of_id, _seq = parse_finding_id(item)
        if issue_of_id != issue:
            raise KarteFormatError(
                f"{block.lineno} 行目 '{block.title}': {DISTINCT_FROM_KEY} の finding ID の "
                f"issue 番号が対象と違う: {item}（対象は issue-{issue}）"
            )
    return tuple(ids)


def review_finding_id(block: Block, issue: int):
    """見出しから finding ID を読む（``### new`` は ``None``＝採番を CLI に委ねる）。"""
    if block.title in NEW_FINDING_TITLES:
        return None
    try:
        issue_of_id, _seq = parse_finding_id(block.title)
    except KarteFormatError as exc:
        raise KarteFormatError(f"{block.lineno} 行目: {exc}") from exc
    if issue_of_id != issue:
        raise KarteFormatError(
            f"{block.lineno} 行目: finding ID の issue 番号が対象と違う: "
            f"{block.title}（対象は issue-{issue}）"
        )
    return block.title


def review_finding_from_block(block: Block, issue: int, finding_id) -> ReviewFinding:
    disposition = parse_disposition(block)
    harm = require_enum(block, "harm", HARM_LEVELS)
    harm_detail = check_harm_detail(
        require_nonempty(block, "harm_detail"), issue=issue, block=block
    )
    return ReviewFinding(
        title=block.title,
        finding_id=finding_id,
        harm=harm,
        harm_detail=harm_detail,
        severity=require_enum(block, "severity", SEVERITIES),
        locus=normalize_locus(block.fields.get("locus", "")),
        summary=require_nonempty(block, "summary"),
        evidence=require_nonempty(block, "evidence"),
        expected=require_nonempty(block, "expected"),
        recheck=require_nonempty(block, "recheck"),
        scope=require_enum(block, "scope", SCOPES),
        lineno=block.lineno,
        status=optional_status(block),
        distinct_from=parse_distinct_from(block, issue),
        disposition=disposition.kind,
        deferred_to=disposition.deferred_to,
        waived_by=disposition.waived_by,
        waived_reason=disposition.waived_reason,
    )
