"""blocker-gate-result/v1 の schema 相当・semantic contract validator。"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Mapping
from uuid import UUID

from .model import (
    ALLOW_REASONS,
    BLOCK_REASONS,
    CLASSIFIER_VERSION,
    ERROR_REASONS,
    POLICY_VERSION,
    RESULT_SCHEMA,
)

_FP = re.compile(r"^sha256:[0-9a-f]{64}$")
_REF = re.compile(r"^[^/]+/[^/#]+#[1-9][0-9]*$")
_WAIVER = re.compile(r"^BW-[0-9]{8}-[0-9]{3,}$")


class ContractError(ValueError):
    pass


def _fail(message: str) -> None:
    raise ContractError(message)


def _date(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        _fail("timestamp must be RFC3339 UTC Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError("timestamp invalid") from exc


def _sorted_unique_refs(values: Any, label: str) -> list[str]:
    if not isinstance(values, list) or any(not isinstance(item, str) or not _REF.fullmatch(item) for item in values):
        _fail(f"{label} invalid")
    if values != sorted(set(values)):
        _fail(f"{label} must be canonical")
    return values


def validate_result_schema(result: Mapping[str, Any]) -> None:
    """外部依存なしで規範 schema の閉じた key/type/enum を検証する。"""
    required = {
        "schema", "policy_version", "classifier_version", "invocation_id", "mode",
        "result", "exit_code", "primary_reason", "reasons", "repository", "subject",
        "binding", "graphql_closing_set", "delivered_message_closing_set", "closing_set",
        "findings", "fetched_at", "completed_at", "pages_complete", "permit_issued",
    }
    if set(result) != required:
        _fail("result keys mismatch")
    if result["schema"] != RESULT_SCHEMA or result["policy_version"] != POLICY_VERSION:
        _fail("schema or policy version mismatch")
    if result["classifier_version"] != CLASSIFIER_VERSION:
        _fail("classifier version mismatch")
    try:
        UUID(str(result["invocation_id"]))
    except ValueError as exc:
        raise ContractError("invocation_id invalid") from exc
    if result["mode"] not in {"issue-start", "pr-merge"}:
        _fail("mode invalid")
    if result["result"] not in {"ALLOW", "BLOCK", "ERROR"}:
        _fail("verdict invalid")
    if result["exit_code"] not in {0, 10, 20}:
        _fail("exit invalid")
    reasons = result["reasons"]
    all_reasons = ALLOW_REASONS | BLOCK_REASONS | ERROR_REASONS
    if not isinstance(reasons, list) or not reasons or len(reasons) != len(set(reasons)):
        _fail("reasons invalid")
    if any(reason not in all_reasons for reason in reasons) or result["primary_reason"] not in all_reasons:
        _fail("unknown reason")
    repository = result["repository"]
    if repository is not None and (not isinstance(repository, str) or repository.count("/") != 1):
        _fail("repository invalid")
    subject = result["subject"]
    if subject is not None:
        if not isinstance(subject, dict) or set(subject) != {"type", "number"}:
            _fail("subject invalid")
        if subject["type"] not in {"issue", "pull_request"} or not isinstance(subject["number"], int) or subject["number"] < 1:
            _fail("subject invalid")
    binding = result["binding"]
    binding_keys = {
        "head_oid", "base_ref_name", "default_branch", "merge_method",
        "intercepted_commit_title_fingerprint", "intercepted_commit_message_fingerprint",
        "message_source_fingerprint", "delivered_message_fingerprint",
        "repository_merge_settings_fingerprint", "operation_fingerprint",
        "snapshot_fingerprint", "attempt",
    }
    if not isinstance(binding, dict) or set(binding) != binding_keys:
        _fail("binding invalid")
    for key in (
        "intercepted_commit_title_fingerprint", "intercepted_commit_message_fingerprint",
        "message_source_fingerprint", "delivered_message_fingerprint",
        "repository_merge_settings_fingerprint", "operation_fingerprint", "snapshot_fingerprint",
    ):
        if binding[key] is not None and not _FP.fullmatch(str(binding[key])):
            _fail(f"{key} invalid")
    if not isinstance(binding["attempt"], int) or not 1 <= binding["attempt"] <= 3:
        _fail("attempt invalid")
    for label in ("graphql_closing_set", "delivered_message_closing_set", "closing_set"):
        _sorted_unique_refs(result[label], label)
    if not isinstance(result["findings"], list):
        _fail("findings invalid")
    finding_keys = {"code", "subject", "path", "fingerprint", "waiver_id"}
    for finding in result["findings"]:
        allowed_finding_keys = (finding_keys, finding_keys | {"waiver_evidence"})
        if not isinstance(finding, dict) or set(finding) not in allowed_finding_keys:
            _fail("finding keys invalid")
        if finding["code"] not in BLOCK_REASONS | ERROR_REASONS:
            _fail("finding code invalid")
        if not isinstance(finding["subject"], str) or not _REF.fullmatch(finding["subject"]):
            _fail("finding subject invalid")
        if not isinstance(finding["path"], list) or any(not _REF.fullmatch(str(item)) for item in finding["path"]):
            _fail("finding path invalid")
        if not _FP.fullmatch(str(finding["fingerprint"])):
            _fail("finding fingerprint invalid")
        waiver_id = finding["waiver_id"]
        if waiver_id is not None and not _WAIVER.fullmatch(str(waiver_id)):
            _fail("waiver id invalid")
        if "waiver_evidence" in finding:
            evidence = finding["waiver_evidence"]
            evidence_keys = {
                "waiver_id", "policy_blob_sha", "waiver_blob_sha", "approval_commit", "expires_at"
            }
            if not isinstance(evidence, dict) or set(evidence) != evidence_keys:
                _fail("waiver evidence invalid")
            if evidence["waiver_id"] != waiver_id:
                _fail("waiver evidence id mismatch")
            if not _WAIVER.fullmatch(str(evidence["waiver_id"])):
                _fail("waiver evidence id invalid")
            for key in ("policy_blob_sha", "waiver_blob_sha"):
                if not _FP.fullmatch(str(evidence[key])):
                    _fail(f"waiver evidence {key} invalid")
            if not re.fullmatch(r"[0-9a-f]{40,64}", str(evidence["approval_commit"])):
                _fail("waiver evidence approval commit invalid")
            _date(evidence["expires_at"])
    _date(result["fetched_at"])
    _date(result["completed_at"])
    if not isinstance(result["pages_complete"], bool) or not isinstance(result["permit_issued"], bool):
        _fail("boolean field invalid")


def validate_result_semantics(result: Mapping[str, Any], process_exit: int) -> Mapping[str, Any]:
    """JSON schema 後に必須の相関検証を行い、検証済み値だけを返す。"""
    validate_result_schema(result)
    verdict = result["result"]
    expected_exit = {"ALLOW": 0, "BLOCK": 10, "ERROR": 20}[verdict]
    if result["exit_code"] != expected_exit or process_exit != expected_exit:
        _fail("process/result exit mismatch")
    reasons = result["reasons"]
    primary = result["primary_reason"]
    if primary not in reasons:
        _fail("primary reason not in reasons")
    graphql = _sorted_unique_refs(result["graphql_closing_set"], "graphql_closing_set")
    delivered = _sorted_unique_refs(result["delivered_message_closing_set"], "delivered_message_closing_set")
    if result["closing_set"] != sorted(set(graphql) | set(delivered)):
        _fail("closing set union mismatch")
    if _date(result["fetched_at"]) > _date(result["completed_at"]):
        _fail("timestamp order invalid")
    findings = result["findings"]
    error_findings = [item for item in findings if item["code"] in ERROR_REASONS]
    unwaived = [item for item in findings if item["code"] in BLOCK_REASONS and item["waiver_id"] is None]
    if verdict == "ALLOW":
        if reasons != [primary] or primary not in ALLOW_REASONS:
            _fail("ALLOW reasons invalid")
        if not result["pages_complete"] or not result["permit_issued"] or error_findings or unwaived:
            _fail("ALLOW correlation invalid")
        waived = [item for item in findings if item["waiver_id"] is not None]
        expected = "WAIVER_APPLIED" if waived else ("NO_CLOSING_EFFECT" if result["mode"] == "pr-merge" and not result["closing_set"] else "NO_VIOLATION")
        if primary != expected:
            _fail("ALLOW primary reason invalid")
        if any(item["code"] != "OPEN_BLOCKER" or "waiver_evidence" not in item for item in waived):
            _fail("waived finding invalid")
    elif verdict == "BLOCK":
        if any(reason not in BLOCK_REASONS for reason in reasons) or primary not in BLOCK_REASONS:
            _fail("BLOCK reasons invalid")
        if result["permit_issued"] or not result["pages_complete"] or error_findings:
            _fail("BLOCK correlation invalid")
        if not unwaived and primary != "AUTO_MERGE_DENIED":
            _fail("BLOCK without finding")
    else:
        if primary not in ERROR_REASONS or not any(reason in ERROR_REASONS for reason in reasons):
            _fail("ERROR reason invalid")
        if any(reason in ALLOW_REASONS for reason in reasons) or result["permit_issued"]:
            _fail("ERROR correlation invalid")
    mode = result["mode"]
    subject = result["subject"]
    binding = result["binding"]
    if mode == "issue-start":
        if subject is not None and subject["type"] != "issue":
            _fail("issue mode subject mismatch")
        if result["closing_set"] or result["graphql_closing_set"] or result["delivered_message_closing_set"]:
            _fail("issue mode closing fields invalid")
        pr_values = [binding[key] for key in ("head_oid", "base_ref_name", "default_branch", "merge_method", "message_source_fingerprint", "delivered_message_fingerprint", "repository_merge_settings_fingerprint")]
        if any(value is not None for value in pr_values):
            _fail("issue mode binding invalid")
    elif subject is not None and subject["type"] != "pull_request":
        _fail("PR mode subject mismatch")
    return result
