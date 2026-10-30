"""ラッパー境界の入力と正規化結果。"""

from dataclasses import dataclass, field
from pathlib import Path
from .usage_types import TokenUsage


@dataclass(frozen=True)
class Request:
    workspace: Path
    settings: Path
    executable: Path
    prompt: str
    print_timeout: int = 120
    conversation: str | None = None
    images: bool = False
    brain: Path | None = None
    caller_state: str | None = None
    permission_root: Path | None = None


@dataclass
class Result:
    run_id: str
    classification: str = "preflight_failed"
    reasons: list[str] = field(default_factory=list)
    agy_exit_code: int | None = None
    status: str | None = None
    conversation_id: str | None = None
    response: str | None = None
    error: str | None = None
    denied_actions: list = field(default_factory=list)
    truncated: bool = False
    artifacts: list[str] = field(default_factory=list)
    agy_version: str | None = None
    stderr_length: int = 0
    workspace_changes: list[dict[str, str]] = field(default_factory=list)
    workspace_change_limitations: list[str] = field(default_factory=list)
    usage: TokenUsage | None = None

    @property
    def exit_code(self) -> int:
        return 0 if self.classification == "success_candidate" else 1
