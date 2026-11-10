"""申し送り記録のキーとハッシュ版。"""

HANDOFF_ISSUE = "handoff_issue"
HANDOFF_COMMENT_URL = "handoff_comment_url"
HANDOFF_CONTENT_HASH = "handoff_content_hash"
HANDOFF_VERIFIED_AT = "handoff_verified_at"
HANDOFF_STATE = "handoff_state"
HANDOFF_KEYS = (HANDOFF_ISSUE, HANDOFF_COMMENT_URL, HANDOFF_CONTENT_HASH,
                HANDOFF_VERIFIED_AT, HANDOFF_STATE)
HANDOFF_HASH_VERSION = 1


def is_handoff_key(key: str) -> bool:
    return key.startswith("handoff_")
