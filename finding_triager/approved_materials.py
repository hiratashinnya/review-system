"""Read the exact reviewed artifact and prior approved reviews covered by a trusted dispatch approval."""

import hashlib
import json
import tomllib
from pathlib import Path

from codex_worktree_exec.committed_artifact import read_committed_artifact
from issue_envelope.model import normalize
from issue_start.phase_dispatch import validate_phase_dispatch
from triage_policy.phases import PHASE_ROUTES, route_of

BOUND = ("issue", "run_id", "target_key", "snapshot_oid")


def _read(root: Path, relative: str, digest: str, kind: str, expected: dict) -> dict:
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError("approved material outside worktree")
    raw = read_committed_artifact(path, root)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("approved material digest changed")
    doc = normalize(tomllib.loads(raw.decode("utf-8")))
    if doc["artifact_type"] != kind or any(doc[k] != expected[k] for k in BOUND):
        raise ValueError("approved material binding mismatch")
    return {"path": relative, "sha256": digest, "content": raw.decode("utf-8")}


def approved_materials(root: Path, marker: dict, phase: str | None = None) -> dict:
    """Validate the native dispatch contract before exporting any document bytes.

    ``marker`` is supplied by the trusted dispatcher, not by the reviewer.
    The caller must preserve this trust boundary and revalidate before use.
    ``phase`` selects the reviewer role, prior receipts and reviewed artifact from the
    phase table; None keeps the implementation-review behavior (#784 passes the phase).
    """
    root = Path(root).resolve(strict=True)
    role = "pr-reviewer" if phase is None else route_of(phase)["reviewer"]
    approval = validate_phase_dispatch(marker, role, root)
    declared = approval.get("triage_phase")
    phase = phase or declared or "review"
    route = route_of(phase)
    if route["reviewer"] != role or declared not in (None, phase):
        raise ValueError("approval triage phase mismatch")
    binding = json.loads((root / marker["binding_file"]).read_bytes())
    expected = binding["expected"]
    reviews = {receipt["phase"]: receipt for receipt in approval["reviews"]}
    materials = {}
    for key in route["prior"]:
        if key not in reviews:
            raise ValueError("missing prior review receipt " + key)
        receipt = reviews[key]
        materials[key] = _read(root, receipt["artifact"], receipt["artifact_digest"],
                               PHASE_ROUTES[key]["artifact_type"], expected)
    if expected.get("artifact_type") != route["artifact_type"]:
        raise ValueError("reviewed artifact type does not match phase")
    reviewed = route["reviewed"]
    if reviewed not in materials:
        materials[reviewed] = _read(root, binding["artifact"], binding["artifact_digest"],
                                    route["artifact_type"], expected)
    if materials[reviewed]["sha256"] != binding["artifact_digest"]:
        raise ValueError("reviewed artifact digest differs from approved receipt")
    return {"issue": approval["issue"], "run_id": approval["run_id"],
            "target_key": approval["target_key"], "snapshot_oid": approval["snapshot_oid"],
            "approval_context": approval["context_id"], "triage_phase": declared,
            "input_digest": binding["artifact_digest"],
            "source_changes": expected.get("source_changes"),
            "materials": materials}
