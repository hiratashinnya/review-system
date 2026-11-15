"""Finding の根拠欄。旧レポートとの互換性を保ちながら値を検証する。"""

from .block_fields import require_nonempty
from .value_codec import check_scalar

REACHABILITY_PATH = "reachability_path"
THREAT_ASSUMPTION = "threat_assumption"


def read_basis(block, key: str) -> str:
    """未記載の旧形式は空文字、明記されたキーは空値/リスト/制御文字を拒否する。"""
    if key not in block.fields:
        return ""
    return check_scalar(require_nonempty(block, key), key)
