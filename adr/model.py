"""ADR 単体の正規化と追跡状態の検査。"""
import datetime
from feedback_ledger.model_normalize import normalize_document
from feedback_ledger.schema_values import has_unsafe_ledger_slug_character
from feedback_ledger.slugify_ref import slugify_topic
from .schema import ADR_SPEC


def normalize(raw):
    data, findings = normalize_document(ADR_SPEC, raw, "ADR")
    errors = [finding.render() for finding in findings]
    if data is None:
        raise ValueError("; ".join(errors))
    if data["schema"] != ADR_SPEC.schema_const:
        errors.append("schema が未対応")
    if len(data["topic"]) > 30:
        errors.append("topic は30字以内")
    match = ADR_SPEC.id_re.fullmatch(data["id"])
    if match and has_unsafe_ledger_slug_character(match.group("slug")):
        errors.append("id に危険な文字")
    if match:
        try:
            datetime.datetime.strptime(match.group("date"), "%Y%m%d")
        except ValueError:
            errors.append("id の日付が不正")
    decision = data["decision"]
    status, number, reason = (decision[key] for key in (
        "tracking_status", "tracking_issue", "no_tracking_reason"))
    if status == "filed" and (number <= 0 or reason):
        errors.append("filed は tracking_issue のみ必須")
    if status == "pending" and (number or reason):
        errors.append("pending は tracking_issue/no_tracking_reason が空であること")
    if status == "not_needed" and (not reason or number):
        errors.append("not_needed は no_tracking_reason のみ必須")
    if errors:
        raise ValueError("; ".join(errors))
    return data


def new_id(data):
    return f"ADR-{data['decided_at']:%Y%m%d}-{slugify_topic(data['topic'])}"
