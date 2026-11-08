"""Codex pr-reviewer の保存済み応答を主カルテへ渡す。"""

from __future__ import annotations

import re
import subprocess
import sys
import uuid
from pathlib import Path

from karte import handoff_header, handoff_path, paths
from karte.errors import KarteUsageError

from .errors import CodexExecError
from . import ingest_diagnostics
from .review_target import progress_target

WARNING_RE = re.compile(
    r"^(?:\s*警告:|\s*オーナーが確定した scope を保持|"
    r"\s*再掲されなかった未解消 finding を引き継ぎ)"
)
def _with_header(body: str, issue: int, round_no: int) -> str:
    header = f"<!-- handoff issue={issue} round={round_no} -->"
    has_header = False
    for line in body.splitlines():
        if line.startswith("### "):
            break
        if handoff_header.HEADER_RE.fullmatch(line):
            has_header = True
    return body if has_header else header + "\n" + body


def _save_handoff(root: Path, body: str, issue: int, round_no: int) -> Path:
    handoff_dir = root / "tmp" / "_handoff"
    report = _with_header(body, issue, round_no)
    handoff_header.check_header(report, issue, round_no)
    handoff_dir.mkdir(parents=True, exist_ok=True)
    path = handoff_path.resolve_reviewer_handoff(
        handoff_dir / f"pr-reviewer--{uuid.uuid4().hex}.md", root
    )
    with path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(report)
    return path


def _ingest(worktree: Path, path: Path) -> tuple[int, str, tuple[str, ...]]:
    result = subprocess.run(
        [sys.executable, "-m", "karte", "ingest-reviewer", "--from", str(path)],
        cwd=worktree, capture_output=True, text=True, check=False,
    )
    lines = (result.stderr + "\n" + result.stdout).splitlines()
    warnings = tuple(dict.fromkeys(line.strip() for line in lines if WARNING_RE.match(line.strip())))
    rejected = [i for i, line in enumerate(lines) if line.strip().startswith("拒否（fail-close）:")]
    detail = ingest_diagnostics.rejection_detail(lines, rejected) if rejected else next(
        (line.strip() for line in reversed(lines) if line.strip()), "karte ingest-reviewer が失敗"
    )
    return result.returncode, detail, warnings


def ingest_codex_output(
    worktree: Path, output_file: Path, expected_issue: int,
    launch_target: tuple[int, int, int],
) -> str:
    """Codex 応答を主checkoutへ保存して既存の ingest-reviewer で検証・取り込む。"""
    try:
        root = paths.main_worktree_root(worktree)
        body = output_file.read_bytes().decode("utf-8")
        if not body.strip():
            raise KarteUsageError("Codex の pr-reviewer 出力が空")
        issue, started_round, round_no = launch_target
        current_issue, current_next_round = progress_target(root)
        current_round = current_next_round - 1
        # 起動時と取り込み時の二重照合で、binding と変化したポインタの両方を拒否する。
        if issue != expected_issue:
            raise KarteUsageError("起動時ポインタの Issue と承認済み expected.issue が不一致")
        if (current_issue, current_round) != (issue, started_round):
            raise KarteUsageError(
                f"起動時ポインタ issue-{issue} round={started_round} と"
                f"取り込み直前 issue-{current_issue} round={current_round} が不一致"
            )
        path = _save_handoff(root, body, issue, round_no)
        code, detail, warnings = _ingest(worktree, path)
    except Exception as error:
        detail = str(error).splitlines()
        raise CodexExecError(
            "CODEX_REVIEW_INGEST_FAILED", detail[-1] if detail else type(error).__name__
        ) from None
    if code:
        raise CodexExecError("CODEX_REVIEW_INGEST_FAILED", f"{path}: {detail}")
    message = f"取り込み済み: {path} (issue-{issue} round {round_no})"
    return "\n".join((message, *warnings))
