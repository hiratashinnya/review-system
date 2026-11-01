"""校正 publication の可視 commit と durability を区別する結果型。"""

from dataclasses import dataclass
from typing import Literal

PublicationPhase = Literal["directory", "marker_create", "marker_sync", "proof_write_verify_sync",
                           "index_write_verify", "index_replace", "index_directory_sync",
                           "marker_unlink", "commit_directory_sync", "complete"]


@dataclass(frozen=True)
class PublicationOutcome:
    state: Literal["not_started", "pending", "committed"]
    proof_sha256: str | None
    durability_confirmed: bool
    phase: PublicationPhase
