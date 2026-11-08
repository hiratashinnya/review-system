"""Strict leaf validators for gitgate's pure argv verbs."""
import re
class GitgateError(Exception):
    """想定外の引数・不正な leaf 値を検知したときに送出する。git は実行されない。"""
BRANCH_NAME_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
# ref は diff 用。`main...HEAD` `HEAD~1` `HEAD^` `origin/main` `main@` 等の一般的な指定を許容する
# 安全 charset（`{ }` 等は含めない＝過剰許可を避ける）。
REF_RE = re.compile(r"^[A-Za-z0-9._/@~^-]+$")
INTEGER_RE = re.compile(r"^[0-9]+$")


def _reject_control_chars(value, what):
    if "\n" in value or "\r" in value or "\0" in value:
        raise GitgateError(f"{what} must not contain newline or NUL characters")


def validate_path(value):
    """`git add -- <paths>` の leaf。`--` 以降に置くためオプション解釈はされない。
    改行・NUL・空文字のみ拒否する（それ以外は pathspec としてそのまま git に渡す）。"""
    if value == "":
        raise GitgateError("path argument must not be empty")
    _reject_control_chars(value, "path argument")
    return value


def validate_branch_name(value):
    _reject_control_chars(value, "branch name")
    if value.startswith("-"):
        raise GitgateError(f"branch name must not start with '-': {value!r}")
    if not BRANCH_NAME_RE.match(value):
        raise GitgateError(
            f"branch name contains disallowed characters (allowed: A-Z a-z 0-9 . _ / -): {value!r}"
        )
    return value


def validate_ref(value):
    _reject_control_chars(value, "ref")
    if value.startswith("-"):
        raise GitgateError(f"ref must not start with '-': {value!r}")
    if not REF_RE.match(value):
        raise GitgateError(
            f"ref contains disallowed characters (allowed: A-Z a-z 0-9 . _ / @ ~ ^ -): {value!r}"
        )
    return value


def validate_integer(value):
    _reject_control_chars(value, "integer")
    if not INTEGER_RE.match(value):
        raise GitgateError(f"expected a non-negative integer, got: {value!r}")
    return value


def validate_grep_pattern(value):
    # `--grep=<pat>` の単一引数としてデータ渡しする（list 渡し＝shell 解釈なし）。改行・NUL のみ拒否。
    _reject_control_chars(value, "grep pattern")
    return value
