"""Read the exact VD and CP covered by a trusted reviewer dispatch approval."""

import hashlib
import json
import tomllib
from pathlib import Path

from codex_worktree_exec.committed_artifact import read_committed_artifact
from issue_envelope.model import normalize
from issue_start.phase_dispatch import validate_phase_dispatch


def approved_materials(root: Path, marker: dict) -> dict:
    """Validate the native dispatch contract before exporting any document bytes.

    ``marker`` is supplied by the trusted dispatcher, not by the reviewer.
    The caller must preserve this trust boundary and revalidate before use.
    """
    root = Path(root).resolve(strict=True)
    approval = validate_phase_dispatch(marker, "pr-reviewer", root)
    binding = json.loads((root / marker["binding_file"]).read_bytes())
    expected = binding["expected"]
    reviews = {receipt["phase"]: receipt for receipt in approval["reviews"]}
    materials = {}
    for phase, kind in (("verification_design", "VerificationDesign"),
                        ("solution_planning", "ChangePlan")):
        receipt = reviews[phase]
        path = root / receipt["artifact"]
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("approved material outside worktree")
        raw = read_committed_artifact(path, root)
        if hashlib.sha256(raw).hexdigest() != receipt["artifact_digest"]:
            raise ValueError("approved material digest changed")
        doc = normalize(tomllib.loads(raw.decode("utf-8")))
        if doc["artifact_type"] != kind or any(doc[k] != expected[k]
                for k in ("issue", "run_id", "target_key", "snapshot_oid")):
            raise ValueError("approved material binding mismatch")
        materials[phase] = {"path": receipt["artifact"], "sha256": receipt["artifact_digest"],
                            "content": raw.decode("utf-8")}
    return {"issue": approval["issue"], "run_id": approval["run_id"],
            "target_key": approval["target_key"], "snapshot_oid": approval["snapshot_oid"],
            "approval_context": approval["context_id"], "triage_phase": approval.get("triage_phase"),
            "input_digest": binding["artifact_digest"],
            "source_changes": expected.get("source_changes"),
            "materials": materials}
