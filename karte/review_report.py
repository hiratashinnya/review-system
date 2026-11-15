"""レビューレポート（``ingest-review`` の入力）全体のパーサ。

各キーの必須／任意の経緯は ``.ai/rationale/karte-module-split.md``「karte/review_report.py」を参照。
"""

from .block_parser import parse_blocks
from .format_error import KarteFormatError
from .review_block import review_finding_from_block, review_finding_id
from .vocabulary import SECTION_FINDINGS


def parse_review(text: str, issue: int) -> list:
    """レビューレポートをパースする（``### F-<issue>-<seq>`` か ``### new`` のブロック列）。

    欠落・不正な ID 形式・要約欠落などはすべて集めて 1 度に報告する。1 件でもあれば
    :class:`KarteFormatError`（fail-close）。冒頭の前書きは無視し、ブロックが 1 件も無いときは
    「finding ブロックが無い」と報告する。

    必須キー: ``harm`` / ``harm_detail`` / ``severity`` / ``scope`` / ``summary`` /
    ``evidence`` / ``expected`` / ``recheck``（``locus`` は任意）。``harm_detail`` は内容も
    検査し（Issue #511）、処置方針・判断経緯の語彙を含むレポートは取り込みごと拒否する。
    この lint と ``scope`` 必須は取り込み側にだけ掛かり、台帳を読む ``parse`` には掛けない。

    任意キー: ``status``（``open`` 既定／``resolved``・解消は明示宣言でのみ成立）・
    ``distinct_from``（再発番判定のペア限定エスケープハッチ）・
    ``disposition`` / ``deferred_to`` / ``waived_by`` / ``waived_reason``（オーナー判断の記録）。
    """
    blocks = parse_blocks(text, allow_preamble=True)
    if not blocks:
        raise KarteFormatError(
            "レビューレポートに finding ブロック（`### F-<issue>-<seq>` か `### new`）が無い"
        )
    findings: list = []
    errors: list = []
    for block in blocks:
        if block.section not in (None, SECTION_FINDINGS):
            errors.append(
                f"{block.lineno} 行目: レビューレポートのセクションは "
                f"'{SECTION_FINDINGS}' のみ（'{block.section}' は不可）"
            )
            continue
        try:
            finding_id = review_finding_id(block, issue)
            findings.append(review_finding_from_block(block, issue, finding_id))
        except KarteFormatError as exc:
            errors.append(str(exc))
    if errors:
        raise KarteFormatError("レビューレポートの検証に失敗:\n  - " + "\n  - ".join(errors))
    return findings
