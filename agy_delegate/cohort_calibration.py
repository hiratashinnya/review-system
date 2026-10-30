"""信頼された一時保全sessionの校正結果を、現在snapshotへ束縛して発行する。"""

from datetime import datetime, timedelta, timezone

from .cohort_executable import executable_sha256
from .cohort_fields import OBSERVATIONS
from .cohort_generator import current_generator_sha256
from .cohort_offline import offline_snapshot_reasons
from .cohort_publication import publish_calibrated_cohort
from .cohort_publication_types import PublicationOutcome
from .cohort_schema import validate_proof, validated_binding, validated_files
from .cohort_validation import checked_hash, exact_object
from .settings_sources import resolve_candidate_sources
from .request_policy import policy_snapshot
from .types import Request
from .windows_binding_values import current_binding_values
from .windows_probe import read_windows_binding


def publish_session_calibration(request: Request, *, begin_source_sha256: str,
                                baseline_binding: dict, baseline_files: dict,
                                observations: dict, owner_record_sha256: str) -> PublicationOutcome:
    """通常run入口からは呼ばず、原memoryを保持中の校正controllerだけが利用する。"""
    checked_hash(begin_source_sha256)
    checked_hash(owner_record_sha256)
    expected_binding = dict(validated_binding(baseline_binding))
    expected_files = {label: dict(value) for label, value in validated_files(baseline_files).items()}
    observed = exact_object(observations, OBSERVATIONS)
    if any(value is not True for value in observed.values()):
        raise ValueError("cohort_observation_unverified")
    if current_generator_sha256() != begin_source_sha256:
        raise ValueError("cohort_generator_mismatch")
    canonical = request.executable.resolve(strict=True)
    executable = executable_sha256(canonical)
    first = read_windows_binding(request)
    binding = current_binding_values(request, first)
    if binding != expected_binding or first["files"] != expected_files:
        raise ValueError("cohort_calibration_baseline_mismatch")
    if binding["executable_sha256"] != executable:
        raise ValueError("cohort_binding_mismatch")
    now = datetime.now(timezone.utc)
    proof = {"protocol": 1, "created_utc": now.isoformat(),
             "expires_utc": (now + timedelta(hours=24)).isoformat(),
             "generator_source_sha256": begin_source_sha256, "binding": binding,
             "files": first["files"], "observations": observed,
             "account_scope": {"declaration": "personal", "owner_record_sha256": owner_record_sha256}}
    validate_proof(proof, now=now)
    resolution = resolve_candidate_sources(canonical)
    root, _, roots = policy_snapshot(request)
    reasons = offline_snapshot_reasons(resolution, proof, root, corpus_roots=roots)
    if reasons:
        raise ValueError("cohort_calibration_snapshot_unverified")
    second = read_windows_binding(request)
    if current_binding_values(request, second) != binding or second["files"] != first["files"]:
        raise ValueError("cohort_calibration_changed")
    if executable_sha256(canonical) != executable:
        raise ValueError("cohort_binding_mismatch")
    if current_generator_sha256() != begin_source_sha256:
        raise ValueError("cohort_generator_mismatch")
    if current_binding_values(request, second) != binding:
        raise ValueError("cohort_binding_mismatch")
    if offline_snapshot_reasons(resolution, proof, root, corpus_roots=roots):
        raise ValueError("cohort_calibration_snapshot_unverified")
    return publish_calibrated_cohort(request.workspace, proof)
