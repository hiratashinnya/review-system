"""Track invalidated reviewer envelopes so cancelled handoffs cannot be replayed."""

from hashlib import sha256
import json
import re

from .active_pointer import read_active
from .errors import KarteUsageError


def _fingerprint(expected):
    payload = json.dumps(expected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()


def for_activation(repo_root, issue, round_no, expected, snapshot, legacy=False):
    """Retain superseded run IDs until the current round is committed."""
    previous = read_active(repo_root)
    if previous.get("issue") != issue or previous.get("round") != round_no:
        return []
    history = previous.get("revoked_review_expectations", [])
    if (not isinstance(history, list) or any(
            not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
            for value in history)):
        raise KarteUsageError("取消済みreview期待値の履歴が不正")
    history = list(history)
    former = previous.get("review_expect")
    if former is not None:
        if not isinstance(former, dict):
            raise KarteUsageError("以前のreview期待値が不正")
        unchanged = (former == expected and previous.get("ac_snapshot") == snapshot
                     and bool(previous.get("legacy_finding_only")) == legacy)
        if not unchanged and _fingerprint(former) not in history:
            history.append(_fingerprint(former))
    if expected is not None and _fingerprint(expected) in history:
        raise KarteUsageError("取消済みまたは差替え済みのreview envelopeは再使用不可。新しい--run-idで再dispatchする")
    return history
