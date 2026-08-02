"""実測 touched-set（変更ファイル＋変更シンボル）の算出。

``append``（診断）は修正の**前**に走るため、その時点では差分が存在しない。実測値は
修正・確認のあと ``close-attempt`` で取り込み、当該 Attempt の ``### Result k`` に記録する。
記録された touched-set は次ラウンド以降の類似判定（実測信号）で使われる
（:mod:`karte.similarity` の docstring 参照）。

粒度は「変更ファイル」＋「変更ファイル::変更シンボル」の 2 段。unified diff の
hunk ヘッダ末尾の関数コンテキスト（``@@ -1,2 +3,4 @@ def build_attrs``）と、
追加/削除行に現れる ``def`` / ``class`` 定義の両方からシンボルを拾う。

依存仕様: :mod:`karte` の docstring（Issue #307「実測信号」）。
"""

from __future__ import annotations

import re
import subprocess

REF_RE = re.compile(r"^[A-Za-z0-9._/@~^-]+$")
HUNK_RE = re.compile(r"^@@[^@]*@@(.*)$")
SYMBOL_RE = re.compile(r"\b(?:async\s+)?(?:def|class|function)\s+([A-Za-z_][A-Za-z0-9_]*)")


class TouchedError(Exception):
    """差分の取得に失敗した（fail-close）。"""


def validate_ref(value: str) -> str:
    text = str(value).strip()
    if not text or text.startswith("-") or not REF_RE.match(text):
        raise TouchedError(
            f"ref に使えない文字列（許可: A-Z a-z 0-9 . _ / @ ~ ^ -・先頭 '-' 不可）: {value!r}"
        )
    return text


def _strip_diff_prefix(path: str) -> str:
    text = path.strip()
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        text = text[1:-1]
    # `git diff` の timestamp 付きヘッダ（`path\t2026-01-01 ...`）を落とす。
    text = text.split("\t", 1)[0].strip()
    if text == "/dev/null":
        return ""
    for prefix in ("a/", "b/", "i/", "w/", "c/", "o/"):
        if text.startswith(prefix):
            return text[len(prefix):]
    return text


def _add(bucket: list, entry: str) -> None:
    if entry and entry not in bucket:
        bucket.append(entry)


def parse_diff(text: str) -> list:
    """unified diff から touched-set（ファイル＋``ファイル::シンボル``）を算出する。"""
    touched: list = []
    current = ""
    pending_old = ""
    for line in str(text).splitlines():
        if line.startswith("--- "):
            pending_old = _strip_diff_prefix(line[4:])
            continue
        if line.startswith("+++ "):
            new_path = _strip_diff_prefix(line[4:])
            current = new_path or pending_old  # 削除ファイルは旧パスを採用
            _add(touched, current)
            continue
        if line.startswith("@@"):
            matched = HUNK_RE.match(line)
            if matched and current:
                for name in SYMBOL_RE.findall(matched.group(1)):
                    _add(touched, f"{current}::{name}")
            continue
        if current and line[:1] in ("+", "-"):
            for name in SYMBOL_RE.findall(line[1:]):
                _add(touched, f"{current}::{name}")
    return sorted(touched)


def git_diff(repo_root, base: str = "HEAD") -> str:
    """``git diff --unified=0 --no-color <base>`` の出力を返す（``shell=False`` の固定 argv）。"""
    ref = validate_ref(base)
    argv = ["git", "diff", "--unified=0", "--no-color", ref]
    try:
        completed = subprocess.run(
            argv, cwd=str(repo_root), shell=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except OSError as exc:  # pragma: no cover - git 不在環境
        raise TouchedError(f"git を起動できない: {exc}") from None
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", "replace").strip()
        raise TouchedError(f"git diff が失敗した（rc={completed.returncode}）: {message}")
    return completed.stdout.decode("utf-8", "replace")
