"""``issue-<N>.md`` の台帳を読み込んで :class:`~karte.model.Karte` にする。"""

from . import model, paths
from .errors import KarteNotFound


def load_karte(repo_root, issue: int):
    """``(path, Karte)``。置き場・台帳が無ければ :class:`KarteNotFound`（未検出＝ガード違反ではない）。

    「未作成」と「触ってはならないパス」は別の終了コードに分ける（運用側が両者を区別できるよう）。
    """
    hint = f"（先に `ingest-review --issue {issue} --round 1` を実行する）"
    try:
        path = paths.karte_path(issue, repo_root)
    except paths.KarteMissing as exc:
        raise KarteNotFound(f"{exc}{hint}") from None
    if not path.is_file():
        raise KarteNotFound(f"カルテが無い: {path}{hint}")
    return path, model.parse(paths.read_text(path))
