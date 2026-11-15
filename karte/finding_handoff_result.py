"""申し送りの照合結果。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VerifyResult:
    valid: bool
    reason: str = ""
