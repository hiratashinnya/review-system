"""レビューア申告 scope の原本（追記専用）。ledger 本体の ``scope`` との差分＝オーナーの覆し。"""

import json

from . import paths

DECLARED_SCOPE_FMT = "issue-{issue}.declared-scope.jsonl"


def _path(issue, repo_root):
    return paths.karte_dir(repo_root, create=True) / DECLARED_SCOPE_FMT.format(issue=issue)


def latest_declared(issue, repo_root) -> dict:
    """finding ID -> 直近のレビューア申告 scope。ファイルが無ければ空。"""
    path = _path(issue, repo_root)
    if not path.is_file():
        return {}
    latest = {}
    for line in paths.read_text(path).splitlines():
        if line.strip():
            record = json.loads(line)
            latest[record["id"]] = record["scope"]
    return latest


def record_declared(issue, repo_root, round_no, declared) -> None:
    """``declared``（finding ID -> scope）を 1 ラウンド分追記する（既存行は書き換えない）。"""
    lines = [
        json.dumps({"round": round_no, "id": fid, "scope": scope}, ensure_ascii=False)
        for fid, scope in sorted(declared.items())
    ]
    path = _path(issue, repo_root)
    text = "\n".join(lines) + "\n"
    if path.exists():
        paths.append_text(path, text)
    else:
        paths.write_text_atomic(path, text)


def overridden(karte, declared) -> list:
    """台帳の scope が最新のレビューア申告と食い違う finding ID（＝オーナーが覆したもの）。"""
    return sorted(
        item.id for item in karte.findings
        if item.id in declared and item.scope != declared[item.id]
    )
