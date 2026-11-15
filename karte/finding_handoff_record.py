"""申し送りの検証記録。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class HandoffRecord:
    handoff_issue: str = ""
    handoff_comment_url: str = ""
    handoff_content_hash: str = ""
    handoff_verified_at: str = ""
    handoff_state: str = ""
