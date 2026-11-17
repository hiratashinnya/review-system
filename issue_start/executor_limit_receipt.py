"""回収receiptがCodex実行者の上限による引き継ぎSTOPであることを確かめる（Issue #829）。"""

SWITCH_ROLES = frozenset({"test-writer", "issue-implementer"})
STOP_KIND = "codex-limit"
_CHECKED_KEYS = ("status", "stop_kind", "stop_reason")


def require_executor_limit_stop(data: bytes) -> None:
    """top-levelの `status: stop`・`stop_kind: codex-limit`・block scalarの `stop_reason` を各1行要求する。

    逐語はblock scalarの字下げ行に閉じるので、逐語中の同名行は判定に入らない。"""
    values: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        key, separator, value = line.partition(":")
        if not separator or line[:1] in ("", " ", "\t", "#", "-") or key not in _CHECKED_KEYS:
            continue
        if key in values:
            raise ValueError(f"duplicate receipt key {key}")
        values[key] = value.strip()
    if (values.get("status") != "stop" or values.get("stop_kind") != STOP_KIND
            or values.get("stop_reason") not in ("|", "|-")):
        raise ValueError("predecessor is not a Codex executor limit stop")
