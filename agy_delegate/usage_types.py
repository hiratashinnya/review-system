"""実測terminalの検証済みtoken使用量。"""

from typing import TypedDict


class TokenUsage(TypedDict):
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    cache_read_tokens: int
    total_tokens: int
