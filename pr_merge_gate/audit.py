"""Pre-use decision のredacted永続audit。"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping


class AuditError(OSError):
    """安全なaudit appendを保証できない。"""


def audit_path(environ: Mapping[str, str] | None = None) -> Path:
    """XDG/HOME contractからaudit.jsonlを解決する。"""
    values = os.environ if environ is None else environ
    state = values.get("XDG_STATE_HOME")
    if state:
        root = Path(state)
    else:
        home = values.get("HOME")
        if not home:
            raise AuditError("HOME/XDG_STATE_HOME missing")
        root = Path(home) / ".local" / "state"
    if not root.is_absolute():
        raise AuditError("state path must be absolute")
    return root / "review-system" / "blocker-gate" / "audit.jsonl"


def append_decision(
    evidence: Mapping[str, Any], *, path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> None:
    """raw command/body/tokenを含まないdecisionを0600 JSONLへappend+fsyncする。"""
    target = audit_path(environ) if path is None else path
    directory = target.parent
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink():
            raise AuditError("audit directory symlink")
        directory.chmod(0o700)
        if target.exists():
            info = target.lstat()
            if stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                raise AuditError("unsafe audit file")
        raw_binding = evidence.get("binding")
        binding: Mapping[str, Any] = raw_binding if isinstance(raw_binding, dict) else {}
        blocker = evidence.get("blocker_evidence")
        record = {
            "schema_version": "pr-merge-audit/1",
            "policy_version": evidence.get("policy_version"),
            "result": evidence.get("result"),
            "reason": evidence.get("reason"),
            "repository": binding.get("repository"),
            "pr_number": binding.get("pr_number"),
            "merge_method": binding.get("merge_method"),
            "transport": binding.get("transport"),
            "operation_fingerprint": binding.get("operation_fingerprint"),
            "invocation_id": blocker.get("invocation_id") if isinstance(blocker, dict) else None,
            "fetched_at": evidence.get("fetched_at"),
            "permit_issued": evidence.get("permit_issued") is True,
            "merge_api_called": False,
            "next_action": evidence.get("next_action"),
        }
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(target, flags, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            payload = json.dumps(
                record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8") + b"\n"
            remaining = memoryview(payload)
            while remaining:
                written = os.write(descriptor, remaining)
                if written < 1:
                    raise OSError("short audit write")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except AuditError:
        raise
    except OSError as exc:
        raise AuditError(str(exc)) from exc
