"""専用 delegate の必読資料だけを symlink をたどらず表示する。"""

import os
import stat
import sys
from pathlib import Path


REFERENCES = (
    ".ai/skills/silent-failure-diagnosis/SKILL.md",
    ".ai/skills/agy-delegate/SKILL.md",
    ".ai/agents/agy-delegate.md",
)
ROOT = Path(__file__).resolve().parent.parent


def read_reference(root: Path, name: str) -> str:
    if name not in REFERENCES:
        raise ValueError("unknown reference")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    directory = os.open(root, flags | os.O_DIRECTORY)
    try:
        parts = name.split("/")
        for part in parts[:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], flags | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("reference is not a regular file")
            data = source.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise ValueError("reference exceeds size limit")
        return data.decode("utf-8")
    finally:
        os.close(directory)


def main() -> int:
    if len(sys.argv) != 1:
        print("reference takes no arguments", file=sys.stderr)
        return 2
    try:
        contents = [(name, read_reference(ROOT, name)) for name in REFERENCES]
    except (OSError, UnicodeError, ValueError) as error:
        print(f"reference unavailable: {error}", file=sys.stderr)
        return 1
    for name, content in contents:
        print(f"\n--- {name} ---\n{content}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
