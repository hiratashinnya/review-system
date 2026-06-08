"""失敗を型で表す（Result / StageOutcome）— S3 fail-close。design/01 §5。

各段は例外を投げず、成功か FailureNotice を値で返す。呼び出し側は match で
Success / Failure を漏れなく分岐し、上流 Failure では副作用を走らせない。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Generic, TypeVar

T = TypeVar("T")


class FailureStage(Enum):
    INTAKE = "intake"
    COMPOSE = "compose"
    EVALUATE = "evaluate"
    VALIDATE = "validate"
    APPLY = "apply"
    LINT = "lint"          # S5 事前 lint も O-14 形式で返す（DD12）


@dataclass(frozen=True, slots=True)
class FailureNotice:                       # O-14 異常系エラー通知
    stage: FailureStage
    reason: str
    subject: Path | None                   # どのファイル/対象（DD13: pathlib.Path）
    next_action: str                       # 実行可能な次手


@dataclass(frozen=True, slots=True)
class Success(Generic[T]):
    value: T


@dataclass(frozen=True, slots=True)
class Failure:
    notice: FailureNotice


# 各段の戻り値。空文書 no-op は Success(EmptyReport) で表す。
StageOutcome = Success[T] | Failure


def ok(value: T) -> Success[T]:
    """成功を短く構築（呼び出し側の意図を明確に）。"""
    return Success(value)


def fail(stage: FailureStage, reason: str, subject: Path | None, next_action: str) -> Failure:
    """fail-close を短く構築。O-14 の素材をそのまま渡す。"""
    return Failure(FailureNotice(stage=stage, reason=reason, subject=subject, next_action=next_action))
