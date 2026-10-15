"""検査に通らなかった理由を、検査ごとに固有の識別子で運ぶ例外。"""

from __future__ import annotations


class CodexExecError(Exception):
    """fail-close の理由。``error_id`` は `CODEX_EXEC_` で始まる検査固有の識別子。"""

    def __init__(self, error_id: str, detail: str = "") -> None:
        super().__init__(f"{error_id}: {detail}" if detail else error_id)
        self.error_id = error_id
        self.detail = detail
