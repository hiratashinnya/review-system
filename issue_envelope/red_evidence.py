"""実行ログとTC bytesを独立レビュー対象TestDesignに束縛する。"""
import hashlib
from feedback_ledger.paths import FeedbackPathError
from .path_binding import committed_bytes


def red_errors(repo, data):
    if data["artifact_type"] != "TestDesign":
        return []
    errors, covered = [], []
    for evidence in data["red_evidence"]:
        covered.append(evidence["tc"])
        if evidence["exit_code"] <= 0 or not evidence["command"].strip():
            errors.append("Red実行commandと非zero exit_codeが必要")
        for key in ("tc", "log"):
            try:
                content = committed_bytes(repo, evidence[key])
                if not content.strip():
                    errors.append(f"Red証拠が空: {evidence[key]}")
                if hashlib.sha256(content).hexdigest() != evidence[key + "_sha256"]:
                    errors.append(f"Red証拠digest不一致: {evidence[key]}")
            except (ValueError, OSError, FeedbackPathError) as exc:
                errors.append(str(exc))
    if len(covered) != len(set(covered)) or set(covered) != set(data["ut_tc"]):
        errors.append("UT-TCとRed証拠は全件一対一対応が必要")
    return [f"{data['id']}: {error}" for error in errors]
