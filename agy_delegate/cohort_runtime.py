"""発行済みcohortのoffline監査→読取専用OS照合を通常runへ接続する。"""

import re

from .cohort_current_binding import compare_current_proof
from .cohort_executable import executable_sha256
from .cohort_generator import current_generator_sha256
from .cohort_offline import offline_snapshot_reasons
from .cohort_storage import read_cohort
from .native_paths import text_sha256
from .request_policy import policy_snapshot, request_path_binding
from .settings_layer_types import SettingsResolution
from .types import Request
from .windows_binding_values import current_binding_values
from .windows_probe import read_windows_binding


def calibrated_runtime_reasons(request: Request, resolution: SettingsResolution) -> list[str]:
    """自己申告の証拠を受けず、proof不正はagy版照会を含め未起動にする。"""
    try:
        proof = read_cohort(request.workspace)
        source = current_generator_sha256()
        if source != proof["generator_source_sha256"]:
            return ["cohort_generator_mismatch"]
        canonical = request.executable.resolve(strict=True)
        expected = proof["binding"]
        root, _, roots = policy_snapshot(request)
        actual = {**request_path_binding(request),
                  "executable_path_sha256": text_sha256(str(canonical)),
                  "executable_sha256": executable_sha256(canonical)}
        if any(actual[key] != expected[key] for key in actual):
            return ["cohort_binding_mismatch"]
        reasons = offline_snapshot_reasons(resolution, proof, root, corpus_roots=roots)
        if reasons:
            return reasons
        observed = read_windows_binding(request)
        reasons = compare_current_proof(proof, current_binding=current_binding_values(request, observed),
                                        current_files=observed["files"], generator_sha256=source)
        reasons.extend(offline_snapshot_reasons(resolution, proof, root, corpus_roots=roots))
        late_binding = request_path_binding(request)
        if late_binding != {key: actual[key] for key in late_binding}:
            reasons.append("cohort_binding_mismatch")
        if executable_sha256(canonical) != actual["executable_sha256"]:
            reasons.append("cohort_binding_mismatch")
        if current_generator_sha256() != source:
            reasons.append("cohort_generator_mismatch")
        return list(dict.fromkeys(reasons))
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        reason = str(error)
        return [reason if re.fullmatch(r"cohort_[a-z_]{1,96}", reason) else "runtime_cohort_unverified"]
