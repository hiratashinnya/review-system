"""限定許可profileを、検査済みworkspace表現から一意に構築する。"""

import re

SAFE_PATH = re.compile(r"[A-Za-z0-9 /_.:\-\u3040-\u309f\u30a0-\u30ff\u3400-\u4dbf\u4e00-\u9fff]+\Z")


def expected_path_rules(path: str) -> dict[str, list[str]]:
    """正規化は呼出元の境界で行い、ここではshell quoting可能な字種だけ許可。"""
    if not isinstance(path, str) or not SAFE_PATH.fullmatch(path):
        raise ValueError("unsafe_workspace_path")
    command = "Get-ChildItem -Name '" + path + "'"
    pattern = "^" + re.escape(command) + "$(?![\\s\\S])"
    return {"allow": [f"read_file({path})", f"write_file({path})", f"command(regex:{pattern})"],
            "ask": [], "deny": [f"write_file({path}/doc-system-v2/nodes)"]}
