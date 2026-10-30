"""内部校正だけが呼ぶ、marker unlink を commitpoint とする publisher。"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .cohort_paths import held_cohort_directory, workspace_id
from .cohort_publication_io import CREATE_FLAGS, create_or_verify_proof, create_private_file
from .cohort_publication_types import PublicationOutcome
from .cohort_schema import canonical_proof_bytes


def publish_calibrated_cohort(workspace: Path, proof: dict, *, now: datetime | None = None
                              ) -> PublicationOutcome:
    """失敗で旧indexを新校正の成功へfallbackせず、未確定markerは消さない。"""
    moment = datetime.now(timezone.utc) if now is None else now
    encoded = canonical_proof_bytes(proof, now=moment)
    wid = workspace_id(workspace)
    if proof["binding"]["workspace_wsl_sha256"] != wid:
        raise ValueError("cohort_workspace_binding_mismatch")
    digest = hashlib.sha256(encoded).hexdigest()
    state, phase = "not_started", "directory"
    try:
        with held_cohort_directory(create=True) as descriptor:
            marker = f"{wid}.publishing"
            phase = "marker_create"
            marker_fd = os.open(marker, CREATE_FLAGS, 0o600, dir_fd=descriptor)
            state, phase = "pending", "marker_sync"
            try:
                os.fchmod(marker_fd, 0o600)
                os.fsync(marker_fd)
            finally:
                os.close(marker_fd)
            os.fsync(descriptor)
            phase = "proof_write_verify_sync"
            create_or_verify_proof(descriptor, digest, encoded)
            phase = "index_write_verify"
            temporary = f"{wid}.{uuid.uuid4().hex}.index.tmp"
            index = json.dumps({"protocol": 1, "proof_sha256": digest},
                               sort_keys=True, separators=(",", ":")).encode()
            create_private_file(descriptor, temporary, index)
            phase = "index_replace"
            os.replace(temporary, f"{wid}.index.json", src_dir_fd=descriptor,
                       dst_dir_fd=descriptor)
            phase = "index_directory_sync"
            os.fsync(descriptor)
            phase = "marker_unlink"
            os.unlink(marker, dir_fd=descriptor)
            state, phase = "committed", "commit_directory_sync"
            os.fsync(descriptor)
        return PublicationOutcome("committed", digest, True, "complete")
    except (OSError, ValueError):
        return PublicationOutcome(state, digest if state == "committed" else None, False, phase)
