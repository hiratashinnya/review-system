"""基準 repository を用いた申し送り先の正規化。"""

import re

REPO = r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"


def normalize_target(target: str, repository: str) -> str | None:
    if not re.fullmatch(REPO, repository):
        return None
    target = target.strip()
    number = re.fullmatch(r"#?([1-9][0-9]*)", target, re.ASCII)
    if number:
        return f"{repository}#{number.group(1)}"
    url = re.fullmatch(rf"https://github\.com/({REPO})/issues/([1-9][0-9]*)", target, re.IGNORECASE | re.ASCII)
    if url and url.group(1).lower() == repository.lower():
        return f"{repository}#{url.group(2)}"
    return None
