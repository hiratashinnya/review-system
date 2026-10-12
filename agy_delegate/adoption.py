"""成果採用条件。意味的検証は呼出 agent が行い、その結果を渡す。"""

from pathlib import Path

from .types import Result


def adoption_reasons(result: Result, *, expected_anchors: dict[str, str],
                     observed_anchors: dict[str, str], substantive_verified: bool,
                     required_artifact: bool = False) -> list[str]:
    """期待アンカーは prompt へ渡さない。文字数から完成を推測しない。"""
    reasons = []
    if result.exit_code != 0:
        reasons.append("execution_not_successful")
    if expected_anchors and (set(expected_anchors) != set(observed_anchors) or
                             any(observed_anchors.get(key) != value
                                 for key, value in expected_anchors.items())):
        reasons.append("anchor_mismatch_or_missing")
    if not substantive_verified:
        reasons.append("substantive_verification_missing")
    if required_artifact and (not result.artifacts or
                              any(not Path(path).is_file() for path in result.artifacts)):
        reasons.append("required_artifact_missing")
    return reasons
