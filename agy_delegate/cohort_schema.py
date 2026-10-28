"""raw 設定やモデル本文を受け入れない cohort proof の厳密 decoder。"""

import json
from datetime import datetime

from .cohort_fields import BINDING_ENUMS, BINDING_HASHES, FILE_FIELDS, OBSERVATIONS, PROOF_FIELDS
from .cohort_fields import MAX_FILE_BYTES
from .cohort_validation import checked_hash, checked_lifetime, checked_protocol, exact_object


def validate_proof(proof: object, *, now: datetime) -> dict:
    """全固定 key/型/enum と校正有効期間が一致した proof だけを返す。"""
    data = exact_object(proof, PROOF_FIELDS)
    checked_protocol(data["protocol"])
    checked_lifetime(data["created_utc"], data["expires_utc"], now)
    checked_hash(data["generator_source_sha256"])
    binding = exact_object(data["binding"], BINDING_HASHES | set(BINDING_ENUMS))
    for key in BINDING_HASHES:
        checked_hash(binding[key])
    for key, expected in BINDING_ENUMS.items():
        if type(binding[key]) is not str or binding[key] != expected:
            raise ValueError("cohort_binding_profile_invalid")
    files = exact_object(data["files"], {"global", "project", "shared"})
    for key, value in files.items():
        entry = exact_object(value, FILE_FIELDS)
        if type(entry["exists"]) is not bool or (key == "global" and not entry["exists"]):
            raise ValueError("cohort_file_presence_invalid")
        for field in FILE_FIELDS - {"exists"}:
            if entry["exists"]:
                checked_hash(entry[field])
            elif entry[field] is not None:
                raise ValueError("cohort_absent_file_metadata_invalid")
    observations = exact_object(data["observations"], OBSERVATIONS)
    if any(value is not True for value in observations.values()):
        raise ValueError("cohort_observation_unverified")
    account = exact_object(data["account_scope"], {"declaration", "owner_record_sha256"})
    if type(account["declaration"]) is not str or account["declaration"] not in {
        "personal", "managed-supported"
    }:
        raise ValueError("cohort_account_unverified")
    checked_hash(account["owner_record_sha256"])
    return data


def canonical_proof_bytes(proof: object, *, now: datetime) -> bytes:
    """validated proof の canonical UTF-8 bytes を64KiB以内で返す。"""
    data = validate_proof(proof, now=now)
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_FILE_BYTES:
        raise ValueError("cohort_file_too_large")
    return encoded
