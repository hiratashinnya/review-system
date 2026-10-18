"""Internal path handling for the karte package."""

import re

TMP_DIRNAME = "tmp"

KARTE_DIRNAME = "_karte"

ACTIVE_FILENAME = "active.json"

ISSUE_RE = re.compile(r"^[1-9][0-9]*$")

KARTE_FILENAME_FMT = "issue-{issue}.md"

class KartePathError(Exception):
    """ガード違反（触ってはならない形のパス）。読み書きは一切行われない。"""

class KarteMissing(KartePathError):
    """置き場（``tmp/`` ／ ``tmp/_karte/``）がまだ**存在しない**（未検出）。

    「触ってはならない形」（symlink・repo 外・traversal）とは区別する。前者は運用上の
    正常な初期状態（まだ ``ingest-review`` していない）で、呼び出し側は EXIT_NOT_FOUND に
    落としたい。:class:`KartePathError` の派生なので、ガード違反として一括で捕まえる
    既存の経路（``except KartePathError``）の fail-close はそのまま効く。
    """

def validate_issue(value) -> int:
    """issue 番号を検証して int で返す。パス構築の唯一の可変部分なので厳格に絞る。"""
    text = str(value)
    if not ISSUE_RE.match(text):
        raise KartePathError(
            f"issue 番号は 1 以上の十進整数のみ（前置ゼロ・符号・空白を認めない）: {value!r}"
        )
    return int(text)
