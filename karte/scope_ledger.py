"""申告 scope の原本（追記専用）への書込みと参照。

* レビューアの申告：``ingest-reviewer`` が取り込みごとに足す（原本。後から書き換えない）。
* オーナーの確定：``decide --scope`` が足す印（``by: owner``）。印のある finding の台帳 scope は
  以後レビューアの申告で上書きしない（オーナーがもう一度 ``decide`` するまで）。
"""

import json

from . import scope_records
from .scope_records import OWNER, exists  # noqa: F401  — exists は呼び出し側が参照する


def _latest(issue, repo_root, *, owner: bool) -> dict:
    latest = {}
    for _line, (_round, finding_id, scope, by) in scope_records.read_records(issue, repo_root):
        if (by == OWNER) == owner:
            latest[finding_id] = scope
    return latest


def latest_declared(issue, repo_root) -> dict:
    """finding ID -> 直近のレビューア申告 scope（オーナーの印は含まない）。"""
    return _latest(issue, repo_root, owner=False)


def owner_scopes(issue, repo_root) -> dict:
    """finding ID -> 直近のオーナー確定 scope（``decide --scope`` で印を残したもの）。"""
    return _latest(issue, repo_root, owner=True)


def record_declared(issue, repo_root, round_no, declared) -> None:
    """``declared``（finding ID -> scope）を 1 ラウンド分追記する。"""
    scope_records.append_lines(issue, repo_root, [
        json.dumps({"round": round_no, "id": fid, "scope": scope}, ensure_ascii=False)
        for fid, scope in sorted(declared.items())
    ])


def record_owner(issue, repo_root, round_no, finding_id, scope) -> None:
    """オーナーが ``decide --scope`` で確定した scope の印を 1 件追記する。"""
    record = {"round": round_no, "id": finding_id, "scope": scope, "by": OWNER}
    scope_records.append_lines(issue, repo_root, [json.dumps(record, ensure_ascii=False)])
