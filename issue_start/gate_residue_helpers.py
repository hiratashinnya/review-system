from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from . import worktree_ledger



def _residue_root(repo_root: Path | None) -> Path:
    """台帳の置き場（main worktree root）を決める。``LedgerError`` はそのまま送出する。"""
    return worktree_ledger.main_worktree_root(
        Path.cwd() if repo_root is None else Path(repo_root)
    )


def _residue_items(entries: Sequence[Mapping[str, Any]]) -> str:
    return "; ".join(
        f"{entry.get('entry_id')}[{entry.get('status')}]"
        f"@{entry.get('worktree_path') or '<unbound>'}"
        for entry in entries
    )
