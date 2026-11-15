"""``karte ingest-reviewer`` の終了コードを、wrapper の失敗識別子へ対応づける（Issue #375 F-375-11）。"""

from __future__ import annotations

from pathlib import Path

from karte.exit_codes import EXIT_INCOMPLETE

from .errors import CodexExecError


def raise_unless_ingested(code: int, detail: str, path: Path, issue: int, round_no: int) -> None:
    """0 以外は例外にする。5（取り込み済み・未完了）は取り込み失敗（その他の非 0）と区別する。"""
    if code == EXIT_INCOMPLETE:
        # 台帳・round は記録済みで期待値も消費済み。取り込み失敗ではなく、同じ handoff の再取り込みも不可。
        raise CodexExecError(
            "CODEX_REVIEW_INGEST_INCOMPLETE",
            f"取り込み済み・未完了（issue-{issue} round {round_no} は台帳へ記録済み・期待値は消費済み）: "
            f"{path}: {detail}。再取り込みせず、主文脈が `karte activate` で期待値を記録し直して再レビューする",
        )
    if code:
        raise CodexExecError("CODEX_REVIEW_INGEST_FAILED", f"{path}: {detail}")
