"""reader検証済proofと内部採取した現在値を、副作用なしで照合する。"""

from datetime import datetime

from .cohort_schema import validate_proof, validated_binding, validated_files
from .cohort_validation import checked_hash


def compare_current_proof(proof: dict, *, current_binding: dict, current_files: dict,
                          generator_sha256: str) -> list[str]:
    """値を出力せず固定理由を返す。実際の期限/account適用範囲はreader責務。"""
    try:
        if type(proof) is not dict or type(proof.get("created_utc")) is not str:
            raise ValueError("cohort_proof_invalid")
        created = datetime.fromisoformat(proof["created_utc"].replace("Z", "+00:00"))
        baseline = validate_proof(proof, now=created)
    except (ValueError, TypeError, KeyError, OverflowError):
        return ["cohort_proof_invalid"]
    reasons = []
    for name, current, checked in [
        ("binding", current_binding, validated_binding),
        ("files", current_files, validated_files),
        ("generator", generator_sha256, checked_hash),
    ]:
        try:
            actual = checked(current)
        except (ValueError, TypeError, KeyError):
            reasons.append(f"cohort_current_{name}_invalid")
            continue
        expected = baseline["generator_source_sha256"] if name == "generator" else baseline[name]
        if actual != expected:
            reasons.append(f"cohort_{name}_mismatch")
    return reasons
