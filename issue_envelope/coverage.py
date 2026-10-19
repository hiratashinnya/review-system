"""IssueごとにVDのACとCPの実装単位の網羅を照合する。"""


def coverage_errors(records):
    grouped = {}
    for data, _ in records:
        grouped.setdefault(data["issue"], []).append(data)
    errors = []
    for issue, nodes in grouped.items():
        plans = [node for node in nodes if node["artifact_type"] == "ChangePlan"]
        if not plans:
            continue
        designs = [node for node in nodes if node["artifact_type"] == "VerificationDesign"]
        approved = {ac for node in designs for ac in node["st_td"]}
        covered = {ac for node in plans for unit in node["work_units"] for ac in unit["ac_refs"]}
        if not approved or covered != approved:
            errors.append(f"AC未対応または未知AC: issue-{issue}")
    return errors
