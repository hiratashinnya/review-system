"""handoff レポートの先頭ヘッダ（共通 envelope を含む）を取り込み先と期待値に照合する。

ヘッダは最初の ``### `` ブロックより前に 1 行で置く::

    <!-- handoff issue=N round=R schema=review-handoff/v1 schema_version=1 producer=pr-reviewer
         phase=P artifact_type=ReviewReport run_id=X target_key=Y input_digest=<sha256>
         snapshot_oid=<40hex> status=ready -->

実際は 1 行。進行ポインタから決まる取り込み先と、レポートが宣言する対象が食い違うものは取り込まない。
別 Issue・別 run・古い snapshot の handoff や、再利用されたファイルを新しいラウンドとして書き込ませない。
共通 envelope の項目は :mod:`karte.review_envelope`（#371 と同じ語彙）で検査し、期待値は
主文脈が進行ポインタへ記録したもの（:mod:`karte.review_expectation`）で、ヘッダの自己申告から補わない。
HTML コメント形式にしているのは、``parse_review`` が前書きの ``key: value`` 行を「解釈できない行」として
拒否するため。
"""

import re

from . import review_envelope
from .errors import KarteUsageError
from .int_args import parse_int

HEADER_RE = re.compile(r"<!--[ \t]*handoff((?:[ \t]+[a-z_]+=\S*)+)[ \t]*-->[ \t]*")
FORMAT_HINT = (
    "ファイルの先頭（最初の `### ` より前）に "
    "`<!-- handoff issue=<N> round=<R> schema=... run_id=... -->` の 1 行が必要"
    "（項目は karte/README.md「review handoff の共通 envelope」）"
)


def _declared(report_text) -> list:
    found = []
    for line in report_text.splitlines():
        if line.startswith("### "):
            break
        match = HEADER_RE.fullmatch(line)
        if match:
            found.append(match.group(1).split())
    return found


def render_header(round_no: int, expected: dict) -> str:
    """期待値（:func:`review_envelope.expected_of`）から handoff の先頭ヘッダ 1 行を作る。"""
    tokens = {
        "issue": expected["issue"], "round": round_no, "schema": review_envelope.SCHEMA,
        "schema_version": review_envelope.SCHEMA_VERSION, "producer": expected["producer"],
        "phase": expected["phase"], "artifact_type": expected["artifact_type"],
        "run_id": expected["run_id"], "target_key": expected["target_key"],
        "input_digest": expected["input_digest"], "snapshot_oid": expected["snapshot_oid"],
        "status": "ready",
    }
    return "<!-- handoff " + " ".join(f"{key}={value}" for key, value in tokens.items()) + " -->"


def _fields(tokens) -> dict:
    fields = {}
    for token in tokens:
        key, _, value = token.partition("=")
        if key in fields:
            raise KarteUsageError(f"handoff のヘッダに `{key}` が重複している")
        fields[key] = value
    return fields


def check_header(report_text, issue: int, round_no: int, expected: dict) -> None:
    """ヘッダが無い・重複・値が取り込み先／期待値と食い違うなら拒否する。

    ``expected`` は主文脈が記録した共通 envelope の期待値。issue と round は取り込み先、
    それ以外（run_id・target_key・input_digest・snapshot_oid・phase 等）は期待値と完全一致を要求する。
    """
    found = _declared(report_text)
    if not found:
        raise KarteUsageError(f"handoff にヘッダが無い（{FORMAT_HINT}）")
    if len(found) > 1:
        raise KarteUsageError("handoff のヘッダ `<!-- handoff ... -->` が重複している")
    fields = _fields(found[0])
    if "issue" not in fields or "round" not in fields:
        raise KarteUsageError(f"handoff のヘッダに issue と round が必要（{FORMAT_HINT}）")
    for key, expected_value in (("issue", issue), ("round", round_no)):
        declared = parse_int(fields[key], f"handoff の {key}")
        if declared != expected_value:
            raise KarteUsageError(
                f"handoff の `{key}={declared}` が取り込み先（{key}={expected_value}）と食い違う"
                "（別 Issue の、または古い・再利用した handoff は取り込まない）"
            )
    try:
        review_envelope.validate_review_envelope(
            {key: value for key, value in fields.items() if key != "round"}, expected
        )
    except ValueError as exc:
        raise KarteUsageError(f"handoff の共通 envelope を拒否: {exc}") from None
