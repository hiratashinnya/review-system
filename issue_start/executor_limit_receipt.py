"""回収receiptが上限による同じroleの再dispatchへ進めるSTOPであることを確かめる（Issue #829）。"""

SWITCH_ROLES = frozenset({"test-writer", "issue-implementer"})
CODEX_LIMIT = "codex-limit"
CLAUDE_LIMIT = "claude-limit"
_CHECKED_KEYS = ("status", "stop_kind", "stop_reason")


def require_limit_stop(data: bytes, role: str) -> None:
    """`codex-limit` はCodex既定role（SWITCH_ROLES）だけ、`claude-limit` は継続検査が扱うroleすべてに通す。"""
    if read_limit_stop_kind(data) == CODEX_LIMIT and role not in SWITCH_ROLES:
        raise ValueError(f"codex-limit is not a stop kind for {role}")


def read_limit_stop_kind(data: bytes) -> str:
    """top-levelの `status: stop`・`stop_kind`・中身のあるblock scalarの `stop_reason` を各1行要求し、種別を返す。

    行は `\\n` だけで分ける（`\\r\\n` は正規化）。逐語は空白で字下げした行に閉じ、判定に入らない。"""
    lines = data.decode("utf-8").replace("\r\n", "\n").split("\n")
    values: dict[str, str] = {}
    for index, line in enumerate(lines):
        key, separator, value = line.partition(":")
        if not separator or line[:1] in ("", " ", "\t", "#", "-") or key not in _CHECKED_KEYS:
            continue
        if key in values:
            raise ValueError(f"duplicate receipt key {key}")
        values[key] = value.strip(" \t")
        if key == "stop_reason" and not _block_has_content(lines[index + 1:]):
            raise ValueError("stop_reason block scalar is empty")
    kind = values.get("stop_kind", "")
    if (values.get("status") != "stop" or kind not in (CODEX_LIMIT, CLAUDE_LIMIT)
            or values.get("stop_reason") not in ("|", "|-")):
        raise ValueError("predecessor is not an executor limit stop")
    return kind


def _block_has_content(following: list[str]) -> bool:
    """block scalarの本体（空行か空白始まりの行の連続）に、`str.isspace()` に当たらない文字を含む行があるか。"""
    for line in following:
        if line and not line.startswith(" "):
            return False
        if line.strip():
            return True
    return False
