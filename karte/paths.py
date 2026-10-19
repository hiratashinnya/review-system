"""カルテ置き場（``tmp/_karte/``）のパス解決・ガード・書込 API。

書込は再検査を維持し、最終要素の検査と open を ``O_NOFOLLOW`` 付き ``os.open`` で行う。
これは最終要素だけを保護するため、親要素の symlink 拒否は ``resolve_within_repo`` など既存
パスガードに依存する。
この module は公開 API を保つ facade で、実装は責務ごとの内部 module に分割している。
"""

from .path_errors import (
    ACTIVE_FILENAME,
    KARTE_DIRNAME,
    KARTE_FILENAME_FMT,
    ISSUE_RE,
    TMP_DIRNAME,
    KarteMissing,
    KartePathError,
    validate_issue,
)
from .path_guard import resolve_within_repo
from .path_io import append_text, read_text, write_text_atomic
from .path_roots import _resolved_root, invoking_worktree_root, main_worktree_root
from .path_storage import active_path, karte_dir, karte_path, writer_lock

__all__ = [
    "ACTIVE_FILENAME",
    "KARTE_DIRNAME",
    "KARTE_FILENAME_FMT",
    "ISSUE_RE",
    "TMP_DIRNAME",
    "KarteMissing",
    "KartePathError",
    "active_path",
    "append_text",
    "invoking_worktree_root",
    "karte_dir",
    "karte_path",
    "main_worktree_root",
    "read_text",
    "resolve_within_repo",
    "validate_issue",
    "write_text_atomic",
    "writer_lock",
]
