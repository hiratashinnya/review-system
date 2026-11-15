"""karte 取り込み子プロセスの実行時間を制限する。"""

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

INGEST_TIMEOUT_SECONDS = 60


def run_ingest(
    run: Callable[..., subprocess.CompletedProcess[str]], worktree: Path, path: Path,
) -> subprocess.CompletedProcess[str]:
    try:
        return run(
            [sys.executable, "-m", "karte", "ingest-reviewer", "--from", str(path)],
            cwd=worktree, capture_output=True, text=True, check=False, timeout=INGEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"karte ingest-reviewer が {INGEST_TIMEOUT_SECONDS} 秒で終了しなかった"
            "（書込みロックの保持・残留の疑い）。台帳・期待値の状態は不明なので "
            "karte status と tmp/_karte/active.json を確かめてから再実行する: "
            f"{str(path)!r}"
        ) from error
