"""レビューア申告 scope の原本（追記専用）。ledger 本体の ``scope`` との差分＝オーナーの覆し。

書込みは常に「既存の全行を検証 → 新しい全体を一時ファイルへ書いて置換」で、途中までしか書かれた
行を作らない。壊れた原本は ``activate --issue N --repair-declared-scope``（主文脈専用）で復旧する。
"""

import json

from . import paths
from .model import KarteFormatError

DECLARED_SCOPE_FMT = "issue-{issue}.declared-scope.jsonl"
BACKUP_SUFFIX = ".bak"
REPAIR_HINT = "（主文脈が `python3 -m karte activate --issue {issue} --repair-declared-scope` で復旧する）"


def ledger_path(issue, repo_root, *, create=False):
    return paths.karte_dir(repo_root, create=create) / DECLARED_SCOPE_FMT.format(issue=issue)


def exists(issue, repo_root) -> bool:
    """この Issue に ``ingest-reviewer`` の原本があるか（置き場が無ければ無い）。"""
    try:
        return ledger_path(issue, repo_root).exists()
    except paths.KarteMissing:
        return False


def record_of(line):
    """1 行を ``(round, id, scope)`` にする。読めない・キー欠落・型違いは ``ValueError``。"""
    try:
        record = json.loads(line)
        round_no, finding_id, scope = record["round"], record["id"], record["scope"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(repr(exc)) from None
    if not (isinstance(round_no, int) and isinstance(finding_id, str) and isinstance(scope, str)):
        raise ValueError("round は整数、id と scope は文字列でなければならない")
    return round_no, finding_id, scope


def _read_records(issue, repo_root):
    """``(path, [(line, record)])``。1 行でも壊れていれば :class:`KarteFormatError`。"""
    try:
        path = ledger_path(issue, repo_root)
    except paths.KarteMissing:  # 置き場ごと無い＝まだ何も取り込んでいない
        return None, []
    if not path.is_file():
        return path, []
    records = []
    for number, line in enumerate(paths.read_text(path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append((line, record_of(line)))
        except ValueError as exc:
            raise KarteFormatError(
                f"申告 scope の原本 {path} の {number} 行目が壊れている（{exc}）。"
                f"台帳との差分を判定できないため拒否する{REPAIR_HINT.format(issue=issue)}"
            ) from None
    return path, records


def latest_declared(issue, repo_root, *, before_round=None) -> dict:
    """finding ID -> 直近のレビューア申告 scope。``before_round`` を渡すとそのラウンド未満だけを見る。

    同一ラウンドの再試行（台帳書込みの失敗後）で、失敗した試行の申告をオーナーの覆しと
    誤判定しないために、判定の基準は「これから取り込むラウンドより前」に限る。
    """
    _, records = _read_records(issue, repo_root)
    latest = {}
    for _line, (round_no, finding_id, scope) in records:
        if before_round is None or round_no < before_round:
            latest[finding_id] = scope
    return latest


def record_declared(issue, repo_root, round_no, declared) -> None:
    """``declared``（finding ID -> scope）を 1 ラウンド分追記する（既存行は書き換えない）。

    既存の全行を先に検証し、末尾改行の有無によらず行を連結し、置換は原子的に行う。
    """
    _, records = _read_records(issue, repo_root)
    lines = [line for line, _record in records]
    lines += [
        json.dumps({"round": round_no, "id": fid, "scope": scope}, ensure_ascii=False)
        for fid, scope in sorted(declared.items())
    ]
    paths.write_text_atomic(ledger_path(issue, repo_root, create=True), "\n".join(lines) + "\n")
