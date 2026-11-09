"""申告 scope の原本（追記専用）への書込みと参照。

* レビューアの申告：``ingest-reviewer`` が取り込みごとに足す（原本。後から書き換えない）。
* オーナーの確定：``decide --scope`` が足す印（``by: owner``）。印のある finding の台帳 scope は
  以後レビューアの申告で上書きしない（オーナーがもう一度 ``decide`` するまで）。
"""

import json

from . import scope_records
from .scope_records import OWNER, exists  # noqa: F401  — exists は呼び出し側が参照する


def _latest(issue, repo_root, *, owner: bool, records=None) -> dict:
    latest = {}
    if records is None:
        records = scope_records.read_records(issue, repo_root)
    for _line, (_round, finding_id, scope, by) in records:
        if (by == OWNER) == owner:
            latest[finding_id] = scope
    return latest


def owner_scopes(issue, repo_root, *, records=None) -> dict:
    """finding ID -> 直近のオーナー確定 scope（``decide --scope`` で印を残したもの）。"""
    return _latest(issue, repo_root, owner=True, records=records)


def record_declared(issue, repo_root, round_no, declared, *, records=None) -> None:
    """``declared``（finding ID -> scope）を 1 ラウンド分追記する。"""
    if records is None:
        records = scope_records.read_records(issue, repo_root)
    existing = {
        fid: scope for _line, (record_round, fid, scope, by) in records
        if record_round == round_no and not by
    }
    lines = [
        json.dumps({"round": round_no, "id": fid, "scope": scope}, ensure_ascii=False)
        for fid, scope in sorted(declared.items())
        if existing.get(fid) != scope
    ]
    if lines:
        scope_records.append_lines(issue, repo_root, lines, records=records)


def arm(issue, repo_root) -> None:
    """原本が無ければ空の原本を作り、その Issue を最初の取り込みの前から保護モードにする。

    原本の有無が保護モードの条件なので、``activate`` がレビューア初回の前に用意する（Issue #375 F-375-03）。
    """
    if not exists(issue, repo_root):
        scope_records.append_lines(issue, repo_root, [])


def record_owner(issue, repo_root, round_no, finding_id, scope) -> None:
    """オーナーが ``decide --scope`` で確定した scope の印を 1 件追記する。"""
    record = {"round": round_no, "id": finding_id, "scope": scope, "by": OWNER}
    scope_records.append_lines(issue, repo_root, [json.dumps(record, ensure_ascii=False)])
