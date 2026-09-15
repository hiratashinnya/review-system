"""Host-only fixer diagnosis/Result transactions (Issue #452 F-452-17).

The ledger is a write-ahead journal. Each karte replacement is an exact append
whose before/after digests are durable before touching the central file. All
cooperative karte writers share its lock; the inner process cannot write either
the journal or the central karte. A retry accepts only those two exact images.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import tempfile

from karte import cli as karte_cli, model, paths, similarity, touched
from . import codex_supervisor_workspace as workspace, worktree_ledger


class KarteBridgeError(RuntimeError):
    def __init__(self, reason: str):
        self.reason = "CODEX_SUPERVISOR_KARTE_" + reason
        self.detail = ""
        super().__init__(self.reason)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def proposal_path(spec) -> Path:
    """Derive the single task-private proposal path; never accept a caller path."""
    if re.fullmatch(r"issue_[1-9][0-9]*_fix_r[1-9][0-9]*", spec.task_key) is None:
        raise KarteBridgeError("IDENTITY_INVALID")
    relative = f"tmp/_diagnosis/{spec.task_key}/proposal.json"
    workspace.assert_no_symlink_components(spec.workspace, relative)
    return spec.workspace / relative


@contextmanager
def _transaction(spec):
    root, known = workspace.one_by_task(spec.repo_root, spec.task_key)
    with worktree_ledger.acquire_ledger_lease(root) as lease:
        entry = next(item for item in lease.document["entries"]
                     if item.get("entry_id") == known["entry_id"])
        if entry.get("agent_type") != "issue-fixer" or entry.get("workspace") != str(spec.workspace):
            raise KarteBridgeError("IDENTITY_INVALID")
        with paths.writer_lock(root):
            path = paths.karte_path(entry["issue"], root)
            yield lease, entry, path


def _read(path: Path) -> str:
    # Files produced by the inner are untrusted, including hardlink aliases.
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    except OSError as exc:
        raise KarteBridgeError("FILE_INVALID") from exc
    try:
        metadata = os.fstat(fd)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                or metadata.st_size > 8 * 1024 * 1024):
            raise KarteBridgeError("FILE_INVALID")
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(fd)


def _proposal(path: Path) -> dict:
    def unique(pairs):
        document = {}
        for key, value in pairs:
            if key in document:
                raise KarteBridgeError("PROPOSAL_MISMATCH")
            document[key] = value
        return document
    try:
        return json.loads(_read(path), object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise KarteBridgeError("PROPOSAL_MISMATCH") from exc


def _replace(path: Path, text: str) -> None:
    fd, name = tempfile.mkstemp(prefix=".karte-bridge-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(name).unlink(missing_ok=True)


def _identity(entry) -> dict:
    return {key: entry[key] for key in (
        "entry_id", "issue", "round", "repository", "workspace", "branch_name",
        "initial_oid", "task_key", "handoff_path",
    )}


def _check_record(entry, record):
    if not isinstance(record, dict) or record.get("identity") != _identity(entry):
        raise KarteBridgeError("IDENTITY_MISMATCH")
    if record.get("state") != "diagnosing" and record.get("thread_id") != entry.get("agent_id"):
        raise KarteBridgeError("THREAD_MISMATCH")


def prepare_diagnosis(spec, *, git_snapshot: dict) -> dict:
    """Bind the initial clean tree, exact findings and central karte before run."""
    with _transaction(spec) as (lease, entry, path):
        current = _read(path)
        karte = model.parse(current)
        findings = list(spec.finding_ids)
        if (not findings or len(findings) != len(set(findings))
                or any(karte.finding(fid) is None or not karte.finding(fid).is_open
                       or entry["round"] not in karte.finding(fid).rounds for fid in findings)):
            raise KarteBridgeError("FINDINGS_MISMATCH")
        existing = entry.get("karte_bridge")
        if existing is not None:
            _check_record(entry, existing)
            if (existing["state"] != "diagnosing" or existing["finding_ids"] != findings
                    or existing["before_sha256"] != _sha(current)
                    or existing["git_snapshot"] != git_snapshot):
                raise KarteBridgeError("STALE_DIAGNOSIS")
            return dict(existing)
        if not git_snapshot["clean"] or git_snapshot["head_oid"] != entry["initial_oid"]:
            raise KarteBridgeError("EDIT_BEFORE_DIAGNOSIS")
        record = {"state": "diagnosing", "identity": _identity(entry),
                  "finding_ids": findings, "before_sha256": _sha(current),
                  "git_snapshot": git_snapshot}
        entry["karte_bridge"] = record
        lease.commit()
        return dict(record)


def diagnosis_prompt(spec, record: dict) -> str:
    """Render host-derived proposal identity or the registered Attempt receipt."""
    if record["state"] == "diagnosing":
        template = {"schema_version": 1, "phase": "diagnosis_proposal",
                    "identity": record["identity"], "finding_ids": record["finding_ids"],
                    "karte_sha256": record["before_sha256"],
                    "root_cause": "replace-with-slug", "change_kind": "logic",
                    "targets": ["path.py::symbol"], "diagnosis": "根本原因・根拠の一行要約"}
        return ("\nHost diagnosis phase: コードを編集せず、中央karteをread-onlyでrenderし、"
                "次のJSONの診断4項目だけを埋めて " + str(proposal_path(spec))
                + " へ書き、終了する。pre_publish handoffはまだ作らない。\n"
                + json.dumps(template, ensure_ascii=False, sort_keys=True))
    return ("\nHost registered diagnosis receipt: "
            + json.dumps({"attempt": record["attempt"], "thread_id": record["thread_id"],
                          "karte_sha256": record["after_sha256"]}, ensure_ascii=False, sort_keys=True)
            + "\nこのAttemptのtargetsだけを修正してpre_publish handoffを作る。"
              "innerからappend/close/commit/pushしない。")


def _apply_journal(path: Path, operation: dict) -> None:
    current = _read(path)
    if _sha(current) == operation["after_sha256"]:
        return
    if _sha(current) != operation["before_sha256"]:
        raise KarteBridgeError("STALE_DIGEST")
    updated = current + operation["append"]
    if _sha(updated) != operation["after_sha256"]:
        raise KarteBridgeError("JOURNAL_TAMPER")
    _replace(path, updated)


def register_diagnosis(spec, *, git_snapshot: dict) -> dict:
    """Append exactly one Attempt after observed successful diagnosis; recover WAL."""
    with _transaction(spec) as (lease, entry, path):
        record = entry.get("karte_bridge")
        _check_record(entry, record)
        if record["git_snapshot"] != git_snapshot:
            raise KarteBridgeError("EDIT_BEFORE_DIAGNOSIS")
        events = entry.get("supervisor_attempts", [])
        latest = events[-1] if events else {}
        if latest.get("state") not in {"diagnosis_ready", "paused_karte_registered"}:
            raise KarteBridgeError("TERMINAL_MISSING")
        if (latest.get("thread_id") != entry.get("agent_id")
                or latest.get("terminal_event") != "turn.completed" or latest.get("exit_code") != 0):
            raise KarteBridgeError("TERMINAL_MISSING")
        proposal = _proposal(proposal_path(spec))
        required = {"schema_version", "phase", "identity", "finding_ids", "karte_sha256",
                    "root_cause", "change_kind", "targets", "diagnosis"}
        if (not isinstance(proposal, dict) or set(proposal) != required
                or type(proposal["schema_version"]) is not int or proposal["schema_version"] != 1
                or proposal["phase"] != "diagnosis_proposal"
                or proposal["identity"] != record["identity"]
                or proposal["finding_ids"] != record["finding_ids"]
                or proposal["karte_sha256"] != record["before_sha256"]):
            raise KarteBridgeError("PROPOSAL_MISMATCH")
        digest = _sha(json.dumps(proposal, sort_keys=True, ensure_ascii=False))
        if record["state"] == "diagnosing":
            current = _read(path)
            if _sha(current) != record["before_sha256"]:
                raise KarteBridgeError("STALE_DIGEST")
            karte = model.parse(current)
            attempt = model.Attempt(
                number=karte.next_attempt_number(), round=entry["round"],
                finding_ids=model.validate_finding_ids(proposal["finding_ids"]),
                root_cause=model.validate_slug(proposal["root_cause"], "root_cause"),
                change_kind=model.validate_change_kind(proposal["change_kind"]),
                targets=model.validate_targets(proposal["targets"]),
                diagnosis=model.check_scalar(proposal["diagnosis"], "diagnosis"))
            if not attempt.diagnosis or any(
                not item or Path(item.split("::", 1)[0]).is_absolute()
                or ".." in Path(item.split("::", 1)[0]).parts for item in attempt.targets):
                raise KarteBridgeError("PROPOSAL_MISMATCH")
            view = similarity.AttemptView(attempt.number, attempt.root_cause,
                                          attempt.change_kind, tuple(attempt.targets), ())
            if similarity.is_saturated(similarity.find_hits(
                    view, karte_cli._priors_for(karte, attempt.finding_ids))):
                raise KarteBridgeError("DIAGNOSIS_SATURATED")
            delta = "\n" + model.render_attempt(attempt)
            record.update(state="registering", thread_id=entry["agent_id"],
                          proposal_sha256=digest, attempt=asdict(attempt), append=delta,
                          after_sha256=_sha(current + delta))
            lease.commit()  # WAL before central mutation.
        if (record["state"] not in {"registering", "registered"}
                or record["proposal_sha256"] != digest):
            raise KarteBridgeError("PROPOSAL_REPLAY")
        _apply_journal(path, record)
        record["state"] = "registered"
        if latest.get("state") != "paused_karte_registered":
            events.append({**latest, "state": "paused_karte_registered",
                           "karte_attempt": record["attempt"]["number"],
                           "karte_sha256": record["after_sha256"]})
        lease.commit()
        return dict(record)


def verify_registered(entry: dict, *, result: dict | None = None,
                      require_closed: bool = False) -> dict:
    """Validate authoritative Attempt/Result and full karte digest on every use."""
    record = entry.get("karte_bridge")
    _check_record(entry, record)
    allowed = {"closed"} if require_closed else {"registered", "closing", "closed"}
    if record["state"] not in allowed:
        raise KarteBridgeError("NOT_REGISTERED")
    relative = f"tmp/_diagnosis/{entry['task_key']}/proposal.json"
    workspace.assert_no_symlink_components(Path(entry["workspace"]), relative)
    proposal = _proposal(Path(entry["workspace"]) / relative)
    if _sha(json.dumps(proposal, sort_keys=True, ensure_ascii=False)) != record["proposal_sha256"]:
        raise KarteBridgeError("PROPOSAL_REPLAY")
    root = paths.main_worktree_root(entry["workspace"])
    current = _read(paths.karte_path(entry["issue"], root))
    expected = record["after_sha256"] if record["state"] == "registered" else record["close"]["after_sha256"]
    if record["state"] == "closing" and _sha(current) == record["close"]["before_sha256"]:
        expected = record["close"]["before_sha256"]
    if _sha(current) != expected:
        raise KarteBridgeError("STALE_DIGEST")
    karte = model.parse(current)
    attempt = karte.attempt(record["attempt"]["number"])
    if attempt is None or asdict(attempt) != record["attempt"]:
        raise KarteBridgeError("ATTEMPT_MISMATCH")
    if result is not None:
        diagnosis = {key: record["attempt"][key] for key in ("root_cause", "change_kind", "targets")}
        diagnosis["karte_attempt"] = attempt.number
        declared_files = {target.split("::", 1)[0] for target in attempt.targets}
        if (result["diagnosis"] != diagnosis or result["finding_ids"] != attempt.finding_ids
                or result["round"] != attempt.round
                or not set(result["changed_files"]).issubset(declared_files)):
            raise KarteBridgeError("HANDOFF_MISMATCH")
    if record["state"] == "closed":
        results = karte.results_for(attempt.number)
        if len(results) != 1 or asdict(results[0]) != record["result"]:
            raise KarteBridgeError("RESULT_MISMATCH")
    return dict(record)


def close_attempt(spec, *, result: dict, head_oid: str) -> dict:
    """Host-only idempotent Result append, using bound pre-edit OID and Attempt."""
    with _transaction(spec) as (lease, entry, path):
        record = verify_registered(entry, result=result)
        events = entry.get("publish_attempts", [])
        pushed = [event for event in events if event.get("state") == "completed"
                  and event.get("action") == "gitgate.push"]
        if (len(pushed) != 1 or pushed[0]["post_snapshot"]["head_oid"] != head_oid
                or pushed[0]["post_snapshot"]["upstream_oid"] != head_oid):
            raise KarteBridgeError("PUSH_MISSING")
        if record["state"] == "registered":
            measured = touched.parse_diff(touched.git_diff(spec.workspace, entry["initial_oid"]))
            if not measured:
                raise KarteBridgeError("EMPTY_DIFF")
            value = model.Result(record["attempt"]["number"], record["finding_ids"],
                                 measured, "fixed", "host publish " + head_oid)
            current = _read(path)
            delta = "\n" + model.render_result(value)
            record.update(state="closing", result=asdict(value),
                          close={"before_sha256": _sha(current), "append": delta,
                                 "after_sha256": _sha(current + delta), "head_oid": head_oid})
            entry["karte_bridge"] = record
            lease.commit()
        if record["close"]["head_oid"] != head_oid:
            raise KarteBridgeError("HEAD_MISMATCH")
        _apply_journal(path, record["close"])
        record["state"] = "closed"
        entry["karte_bridge"] = record
        lease.commit()
        return verify_registered(entry, result=result, require_closed=True)
