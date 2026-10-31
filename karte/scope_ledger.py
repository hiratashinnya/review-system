"""レビューア申告 scope の原本（追記専用）。ledger 本体の ``scope`` との差分＝オーナーの覆し。"""

import json

from . import paths
from .model import KarteFormatError

DECLARED_SCOPE_FMT = "issue-{issue}.declared-scope.jsonl"


def _path(issue, repo_root, *, create=False):
    return paths.karte_dir(repo_root, create=create) / DECLARED_SCOPE_FMT.format(issue=issue)


def exists(issue, repo_root) -> bool:
    """この Issue に ``ingest-reviewer`` の原本があるか（置き場が無ければ無い）。"""
    try:
        return _path(issue, repo_root).exists()
    except paths.KarteMissing:
        return False


def _parse_line(line, path):
    try:
        record = json.loads(line)
        return record["round"], record["id"], record["scope"]
    except (ValueError, KeyError, TypeError) as exc:
        raise KarteFormatError(
            f"申告 scope の原本 {path} が壊れている（{exc!r}）。台帳との差分を判定できないため拒否する"
        ) from None


def latest_declared(issue, repo_root, *, before_round=None) -> dict:
    """finding ID -> 直近のレビューア申告 scope。``before_round`` を渡すとそのラウンド未満だけを見る。

    同一ラウンドの再試行（台帳書込みの失敗後）で、失敗した試行の申告をオーナーの覆しと
    誤判定しないために、判定の基準は「これから取り込むラウンドより前」に限る。
    """
    path = _path(issue, repo_root)
    if not path.is_file():
        return {}
    latest = {}
    for line in paths.read_text(path).splitlines():
        if line.strip():
            round_no, finding_id, scope = _parse_line(line, path)
            if before_round is None or round_no < before_round:
                latest[finding_id] = scope
    return latest


def record_declared(issue, repo_root, round_no, declared) -> None:
    """``declared``（finding ID -> scope）を 1 ラウンド分追記する（既存行は書き換えない）。"""
    lines = [
        json.dumps({"round": round_no, "id": fid, "scope": scope}, ensure_ascii=False)
        for fid, scope in sorted(declared.items())
    ]
    path = _path(issue, repo_root, create=True)
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
