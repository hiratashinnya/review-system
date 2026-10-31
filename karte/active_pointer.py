"""進行ポインタ ``tmp/_karte/active.json`` の読み書き。

設計理由は [.ai/rationale/karte-module-split.md](../.ai/rationale/karte-module-split.md)。
"""

import json

from . import paths
from .errors import KarteUsageError


def read_active(repo_root, *, required: bool = False) -> dict:
    """進行ポインタを読む。

    ``required``＝``--issue`` / ``--round`` の補完に使う（これが唯一の情報源）とき True。
    ポインタが**まだ無い**場合に ``{}`` を返さず :class:`KarteUsageError` を送出する。

    **壊れている場合は ``required`` によらず常に拒否する**（K-13/K-14/K-15）。壊れたポインタを
    「無い」と同じ ``{}`` に潰すと、補完が沈黙のうちに別 Issue・別ラウンドへ倒れ、誤った台帳を
    書き換えても観測できない。「まだ無い」（正常な初期状態）と「壊れている」は別物として扱う。
    """
    try:
        path = paths.active_path(repo_root)
    except paths.KarteMissing as exc:
        if required:
            raise KarteUsageError(f"進行ポインタが無い: {exc}") from None
        return {}
    if not path.is_file():
        if required:
            raise KarteUsageError(
                f"進行ポインタ {path} が無い"
                "（先に `ingest-review --issue N --round R` を明示指定で実行する）"
            )
        return {}
    try:
        data = json.loads(paths.read_text(path))
    except ValueError as exc:
        raise KarteUsageError(
            f"進行ポインタ {path} が JSON として壊れている: {exc}"
            "（補完に使えないため取り込まない。ポインタを作り直すこと）"
        ) from None
    if not isinstance(data, dict):
        raise KarteUsageError(
            f"進行ポインタ {path} の中身が JSON オブジェクトでない: {type(data).__name__}"
        )
    return data


def write_active(repo_root, issue: int, round_no: int) -> None:
    path = paths.active_path(repo_root, create_dir=True)
    paths.write_text_atomic(
        path, json.dumps({"issue": int(issue), "round": int(round_no)}, ensure_ascii=False) + "\n"
    )
