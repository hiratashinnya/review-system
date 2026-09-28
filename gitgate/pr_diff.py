"""全量 PR 差分を RTK 経由で取得し、大きな結果をファイルへ保存する。"""

import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path


MAX_INLINE_DIFF_BYTES = 4096
PR_NUMBER_RE = re.compile(r"[1-9][0-9]{0,9}", re.ASCII)


class PrDiffError(ValueError):
    """PR 番号・保存先が安全な条件を満たさない。"""


def validate_pr_number(value):
    """ASCII 数字の正の PR 番号を、先頭ゼロなし・最大10桁で検証する。"""
    if not PR_NUMBER_RE.fullmatch(value):
        raise PrDiffError("PR number must be 1-10 ASCII digits, positive, without leading zeroes")
    return value


def _save_diff(pr_number, content):
    directory = Path("tmp") / "pr-diffs"
    tmp_descriptor = directory_descriptor = file_descriptor = -1
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        os.makedirs("tmp", exist_ok=True)
        tmp_descriptor = os.open("tmp", directory_flags)
        try:
            os.mkdir("pr-diffs", dir_fd=tmp_descriptor)
        except FileExistsError:
            pass
        directory_descriptor = os.open(
            "pr-diffs", directory_flags, dir_fd=tmp_descriptor
        )
        filename = f"pr-{pr_number}-{uuid.uuid4().hex}.diff"
        file_descriptor = os.open(
            filename,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_descriptor,
        )
        returned_path = (directory / filename).as_posix()
        with os.fdopen(file_descriptor, "wb") as output:
            file_descriptor = -1
            output.write(content)
            opened_file = os.fstat(output.fileno())
            returned_file = os.stat(returned_path)
            if (opened_file.st_dev, opened_file.st_ino) != (
                returned_file.st_dev,
                returned_file.st_ino,
            ):
                raise PrDiffError("PR diff path no longer identifies the created file")
        return returned_path
    except (OSError, AttributeError, TypeError) as error:
        raise PrDiffError("refusing unsafe PR diff storage") from error
    finally:
        for descriptor in (file_descriptor, directory_descriptor, tmp_descriptor):
            if descriptor >= 0:
                os.close(descriptor)


def run_pr_diff(args):
    """Run the approved RTK command and emit either complete bytes or file metadata JSON."""
    if len(args) != 1:
        raise PrDiffError("`show-pr-diff` requires exactly one argument: <PR number>")
    pr_number = validate_pr_number(args[0])
    command = ["rtk", "gh", "pr", "diff", pr_number, "--no-compact"]
    try:
        completed = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, shell=False
        )
    except OSError as exc:
        raise PrDiffError(f"could not execute RTK for PR diff: {exc}") from exc
    if completed.returncode:
        sys.stderr.buffer.write(completed.stderr)
        return completed.returncode
    content = completed.stdout
    if len(content) <= MAX_INLINE_DIFF_BYTES:
        sys.stdout.buffer.write(content)
        return 0
    try:
        path = _save_diff(pr_number, content)
    except OSError as exc:
        raise PrDiffError(f"could not save complete PR diff: {exc}") from exc
    lines = content.count(b"\n") + bool(content and not content.endswith(b"\n"))
    result = {
        "path": path,
        "bytes": len(content),
        "lines": lines,
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
    return 0
