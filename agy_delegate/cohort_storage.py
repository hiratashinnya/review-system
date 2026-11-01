"""固定 private cohort index/proof を二読して検証済み辞書を返す。"""

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from .cohort_paths import held_cohort_directory, workspace_id
from .cohort_private_io import file_identity, private_file_bytes, require_no_marker
from .cohort_schema import canonical_proof_bytes, validate_proof
from .cohort_validation import checked_hash, checked_protocol, exact_object
from .strict_json import load_json


def read_cohort(workspace: Path, *, now: datetime | None = None) -> dict:
    """未確定印、欠落、改変、期限切れは旧 proof へ戻らず固定理由で拒否する。"""
    moment = datetime.now(timezone.utc) if now is None else now
    wid = workspace_id(workspace)
    try:
        with held_cohort_directory() as descriptor:
            before = file_identity(os.fstat(descriptor))
            require_no_marker(descriptor, wid)
            first = _read_pair(descriptor, wid, moment)
            second = _read_pair(descriptor, wid, moment)
            require_no_marker(descriptor, wid)
            if first != second or before != file_identity(os.fstat(descriptor)):
                raise ValueError("cohort_snapshot_changed")
    except OSError:
        raise ValueError("cohort_storage_unavailable") from None
    return first[0]


def _read_pair(descriptor: int, wid: str, now: datetime) -> tuple:
    index_bytes, index_identity = private_file_bytes(descriptor, f"{wid}.index.json")
    index = exact_object(_decode(index_bytes), {"protocol", "proof_sha256"})
    checked_protocol(index["protocol"])
    digest = checked_hash(index["proof_sha256"])
    proof_bytes, proof_identity = private_file_bytes(descriptor, f"{digest}.json")
    if hashlib.sha256(proof_bytes).hexdigest() != digest:
        raise ValueError("cohort_proof_digest_mismatch")
    proof = validate_proof(_decode(proof_bytes), now=now)
    if canonical_proof_bytes(proof, now=now) != proof_bytes:
        raise ValueError("cohort_proof_noncanonical")
    if proof["binding"]["workspace_wsl_sha256"] != wid:
        raise ValueError("cohort_workspace_binding_mismatch")
    return proof, index_bytes, index_identity, proof_identity


def _decode(content: bytes) -> object:
    try:
        return load_json(content.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise ValueError("cohort_json_invalid") from None
