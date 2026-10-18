"""`.ai/guidance/` から PF 常駐入口を生成し、drift を検査する。

Claude は公式 ``@`` import で共通原稿を直接読むため、この生成対象には含めない。
`.ai/rationale/`、`.ai/troubleshooting/`、`.ai/schema/` は非活性の共有記録／契約で
あり、常駐 guidance の入力にも生成物にも含めない。
pre-commit 向け検査は working tree を参照せず staged index だけを読み、自動生成も
自動 stage も行わない。
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from ai_layout import NON_ACTIVE_SHARED_DIRS

from .cli import _print_errors, main
from .filesystem import _filesystem_loader, check, render
from .git_index import _index_loader, _run_git, _staged_paths
from .rendering import (
    _body,
    _principles_marker,
    _sha256,
    _source_dependency_errors,
    rendered_bytes,
)
from .sources import (
    COMMON_SOURCE,
    NON_GUIDANCE_SHARED_DIRS,
    PRINCIPLES_MARKER_RE,
    PRINCIPLES_SOURCE,
    REPO_ROOT,
    TARGETS,
)
from .staged import staged_check
