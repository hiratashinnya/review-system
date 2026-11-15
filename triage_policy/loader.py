"""Read-only policy loader and digest used to bind trusted owner approval."""

import hashlib
import json
from pathlib import Path

from .contract import validate_policy

DEFAULT_POLICY = (Path(__file__).resolve().parent.parent
                  / ".ai" / "guidance" / "triage-policy-v1.json")


def policy_digest(policy: dict) -> str:
    canonical = json.dumps(policy, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_policy(path: Path = DEFAULT_POLICY) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_policy(policy)
    if errors:
        raise ValueError("invalid triage policy: " + ", ".join(errors))
    return policy
