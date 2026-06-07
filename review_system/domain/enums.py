"""閉じた語彙＝Enum（生文字列比較を一掃）。design/01 §2。"""
from __future__ import annotations

from enum import Enum, IntEnum


class DocumentType(Enum):
    CODE = "code"
    SPEC = "spec"
    MINUTES = "minutes"


class Severity(IntEnum):           # 順序あり（error > warning > info）→ 方向ゲートで大小比較
    INFO = 1
    WARNING = 2
    ERROR = 3


class Determinism(Enum):
    DETERMINISTIC = "deterministic"
    TRADEOFF = "tradeoff"
    JUDGMENT = "judgment"


class OverrideRule(Enum):
    LOCKED = "locked"
    TIGHTEN_ONLY = "tighten-only"  # 既定
    OPEN = "open"


class ApplicationMode(Enum):
    AUTO_FIX_LOG_ONLY = "auto_fix_log_only"   # 🤖
    AUTO_FIX_SUGGEST = "auto_fix_suggest"     # ✋
    HUMAN_ONLY = "human_only"                 # 💬


class TriageBucket(Enum):
    AUTO = "auto"                 # 🤖
    APPROVE = "approve"           # ✋
    JUDGE = "judge"               # 💬
    UNCLASSIFIED = "unclassified" # ❓


class ReviewDecision(Enum):
    APPROVE = "approve"
    MODIFY = "modify"
    REJECT = "reject"
    OUT_OF_SCOPE = "out_of_scope"


class InheritanceLayer(Enum):
    ORG = "org"
    TEAM = "team"
    PROJECT = "project"


class FixOrigin(Enum):            # 確定fix の生成元（Q21）
    DETERMINISTIC_TOOL = "tool"
    LLM = "llm"
