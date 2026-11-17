"""回収receiptがCodex実行者の上限による引き継ぎSTOPであることを確かめる（Issue #829）。"""

SWITCH_ROLES = frozenset({"test-writer", "issue-implementer"})
STOP_KIND = "codex-limit"
_CHECKED_KEYS = ("status", "stop_kind", "stop_reason")


def require_executor_limit_stop(data: bytes) -> None:
    """top-levelの `status: stop`・`stop_kind: codex-limit`・中身のあるblock scalarの `stop_reason` を各1行要求する。

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
    if (values.get("status") != "stop" or values.get("stop_kind") != STOP_KIND
            or values.get("stop_reason") not in ("|", "|-")):
        raise ValueError("predecessor is not a Codex executor limit stop")


def _block_has_content(following: list[str]) -> bool:
    """block scalarの本体（空行か空白始まりの行の連続）に、空白以外を含む行があるか。"""
    for line in following:
        if line and not line.startswith(" "):
            return False
        if line.strip():
            return True
    return False
