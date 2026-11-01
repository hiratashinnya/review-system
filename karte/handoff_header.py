"""handoff レポートの先頭ヘッダ ``<!-- handoff issue=N round=R -->`` を取り込み先と照合する。

進行ポインタから決まる取り込み先と、レポートが宣言する対象が食い違うものは取り込まない。
別 Issue のレポートや、古い・再利用された handoff ファイルを新しいラウンドとして書き込ませない。
ヘッダは最初の ``### `` ブロックより前に 1 行で置く。HTML コメント形式にしているのは、
``parse_review`` が前書きの ``key: value`` 行を「解釈できない行」として拒否するため。
"""

import re

from .errors import KarteUsageError
from .verb_support import parse_int

HEADER_RE = re.compile(r"^<!--\s*handoff\s+issue=(\S+)\s+round=(\S+)\s*-->\s*$")
FORMAT_HINT = "ファイルの先頭（最初の `### ` より前）に `<!-- handoff issue=<N> round=<R> -->` の 1 行が必要"


def _declared(report_text) -> list:
    found = []
    for line in report_text.splitlines():
        if line.startswith("### "):
            break
        match = HEADER_RE.match(line)
        if match:
            found.append(match.groups())
    return found


def check_header(report_text, issue: int, round_no: int) -> None:
    """ヘッダが無い・重複・値が取り込み先（``issue`` と次の ``round_no``）と食い違うなら拒否する。"""
    found = _declared(report_text)
    if not found:
        raise KarteUsageError(f"handoff にヘッダが無い（{FORMAT_HINT}）")
    if len(found) > 1:
        raise KarteUsageError("handoff のヘッダ `<!-- handoff ... -->` が重複している")
    declared_issue, declared_round = found[0]
    for key, text, expected in (("issue", declared_issue, issue), ("round", declared_round, round_no)):
        declared = parse_int(text, f"handoff の {key}")
        if declared != expected:
            raise KarteUsageError(
                f"handoff の `{key}={declared}` が取り込み先（{key}={expected}）と食い違う"
                "（別 Issue の、または古い・再利用した handoff は取り込まない）"
            )
