"""Compatibility facade for Issue-start gate consumers."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from blocker_gate.contract import ContractError, validate_result_semantics
from blocker_gate.github import GitHubCollector
from blocker_gate.resolver import evaluate_snapshot
from blocker_gate.snapshot import (
    RepositorySnapshotError,
    parse_repository_snapshot,
    project_issue_snapshot,
)

from . import worktree_ledger
from .gated_roles import GATED_ROLES
from .gate_blocker_report import _blocker_report
from .gate_caller import _caller_agent_type
from .gate_collectors import IssueStartGitHubCollector, SnapshotIssueMetadata
from .gate_dispatch import parse_dispatch_payload
from .gate_evaluate import evaluate_issue_start
from .gate_evidence import _error_evidence, fail_closed
from .gate_git import _canonical_github_repository, _git_output, _run_git
from .gate_isolation_dispatch import _parse_isolation_only
from .gate_ledger_metadata import _ledger_metadata
from .gate_ledger_records import record_isolation_only_entry, record_open_entry
from .gate_manifest import (
    _agent_types,
    _claude_request,
    _entries,
    _isolation_only_entries,
    _managed_entries,
    _manifest,
    _request,
)
from .gate_markers import _fix_binding, _marker_payload
from .gate_residue import assert_no_worktree_residue
from .gate_residue_helpers import _residue_items, _residue_root
from .gate_release import (
    DEFERRED_RELEASE_FAILURE_MARKER,
    DEFERRED_RELEASE_FAILURE_THRESHOLD,
    _deferred_release_failure_count,
    _finish_deferred_releases,
)
from .gate_snapshot_policy import _assert_snapshot_fresh, _snapshot_fallback_required
from .gate_snapshot_read import read_repository_snapshot
from .gate_support import (
    BINDING_MARKER,
    ENTRYPOINT_MANIFEST,
    FIX_BINDING_MARKER,
    ISSUE_START_POLICY_VERSION,
    MANIFEST_SCHEMA_VERSION,
    SNAPSHOT_BRANCH,
    SNAPSHOT_FALLBACK_REASON,
    SNAPSHOT_GIT_TIMEOUT_SECONDS,
    SNAPSHOT_MAX_AGE_SECONDS,
    SNAPSHOT_PATH,
    SNAPSHOT_REMOTE_REF,
    IssueStartError,
    IssueStartRequest,
    IsolationOnlyAck,
    _BRANCH,
    _HANDOFF_PATH,
    _HTTPS_REMOTE,
    _OID,
    _REF,
    _REPOSITORY,
    _SSH_REMOTE,
)
from .gate_transport import _managed_transport, _require_transport_available
from .gate_validation import _validate_isolation, _validate_tool_input_shape
