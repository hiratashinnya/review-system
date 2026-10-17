"""宣言に基づく正規化と工程契約の単体検査。"""
import re
from feedback_ledger.model_normalize import normalize_document
from .schema import CONTRACTS, SPECS


def normalize(raw):
    kind = raw.get("artifact_type") if isinstance(raw, dict) else None
    if kind not in SPECS:
        raise ValueError("artifact_type が未対応")
    spec = SPECS[kind]
    data, findings = normalize_document(spec, raw, kind)
    errors = [f.render() for f in findings]
    if data is None:
        raise ValueError("; ".join(errors))
    producer, phase, prefix = CONTRACTS[kind]
    for key, expected in (("producer", producer), ("phase", phase),
                          ("schema", spec.schema_const), ("schema_version", 1)):
        if data[key] != expected:
            errors.append(f"{key} が契約と不一致")
    if data["issue"] <= 0 or not spec.id_re.fullmatch(data["id"]):
        errors.append("issue/id が不正")
    if not re.fullmatch(rf"{prefix}-{data['issue']}(?:-[^/\\]+)?", data["id"]):
        errors.append("id と issue が不一致")
    if not re.fullmatch(r"[0-9a-f]{40}", data["snapshot_oid"]):
        errors.append("snapshot_oid は40桁のOIDが必要")
    if not re.fullmatch(r"[0-9a-f]{64}", data["input_digest"]):
        errors.append("input_digest はsha256が必要")
    if data["next_expected_artifact"] not in ("", *CONTRACTS):
        errors.append("next_expected_artifact が未対応")
    if data["status"] == "stop" and not data["stop_reason"]:
        errors.append("STOPの理由が必要")
    if data["status"] == "ready" and data["stop_reason"]:
        errors.append("ready にstop_reasonは許可されない")
    if kind == "VerificationDesign" and not data["parent"]:
        if not data["st_td"] or not data["st_tc"]:
            errors.append("VDルートにはST-TD/ST-TCが必須")
    if kind == "VerificationDesign" and bool(data["it_td"]) != bool(data["it_tc"]):
        errors.append("IT-TD/IT-TCは対で必要")
    if kind == "InvestigationReport" and data["investigation_required"] not in (0, 1):
        errors.append("investigation_required は0または1")
    if kind == "TestDesign" and not data["work_unit"].strip():
        errors.append("TestDesignには単一work_unitが必要")
    if errors:
        raise ValueError("; ".join(errors))
    return data
