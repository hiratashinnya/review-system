"""主worktreeを共有する読み取り専用工程の受理値。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ReadOnlyPhaseAck:
    agent_type: str
    entrypoint: str
