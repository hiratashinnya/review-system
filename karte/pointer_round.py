"""進行ポインタから「次に取り込むラウンド」を決める（``ingest-reviewer`` 用）。"""

from . import paths
from .active_pointer import read_active
from .errors import KarteUsageError
from .verb_support import parse_int


def next_round(repo_root, issue: int) -> int:
    """取り込み済みの最新ラウンド（進行ポインタの ``round``。0＝未取込）＋1。

    ``round`` の欠落・非数値、Issue の不一致は拒否する（呼び出し側のロックの内側で呼ぶ）。
    """
    active = read_active(repo_root, required=True)
    if "round" not in active:
        raise KarteUsageError("進行ポインタに 'round' が無い（`activate --issue N` で作り直す）")
    last = parse_int(active["round"], "進行ポインタの round", minimum=0)
    if "issue" not in active or paths.validate_issue(active["issue"]) != issue:
        raise KarteUsageError(f"進行ポインタが指す issue-{active.get('issue')} と対象 issue-{issue} が食い違う")
    return last + 1
