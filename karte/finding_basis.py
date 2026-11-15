"""Finding の根拠欄。旧レポートとの互換性を保ちながら値を検証する。"""

from .block_fields import require_nonempty
from .value_codec import check_scalar

REACHABILITY_PATH = "reachability_path"
THREAT_ASSUMPTION = "threat_assumption"


def read_basis(block, key: str, *, ledger: bool = False) -> str:
    """旧形式の未記載と台帳の空欄は許容。reviewer の明記した空値は拒否。"""
    if key not in block.fields:
        return ""
    raw = block.fields[key]
    if ledger and isinstance(raw, str) and not raw.strip():
        return ""
    return check_scalar(require_nonempty(block, key), key)
