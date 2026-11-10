"""Immutable ID generation and conservative duplicate screening."""

import re
import unicodedata
from difflib import SequenceMatcher

from feedback_ledger.slugify_ref import slugify_topic

IDENTITY = re.compile(r"ADV-(\d{8})-(.+)\Z")
SLUG = re.compile(r"[^\s/\\:*?\"<>|\\'()\[\]{}（）「」【】〔〕\x00-\x1f]+")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def identifier(topic: str, created_on: str) -> str:
    from datetime import date
    if not DATE.fullmatch(created_on):
        raise ValueError("created_on must be ISO YYYY-MM-DD")
    date.fromisoformat(created_on)
    if not isinstance(topic, str) or not topic.strip() or len(topic) > 30:
        raise ValueError("topic must be a concrete summary of 1-30 characters")
    if any(unicodedata.category(c).startswith("C") for c in topic):
        raise ValueError("topic contains control or format characters")
    slug = slugify_topic(topic)
    if not slug or not SLUG.fullmatch(slug):
        raise ValueError("topic has no safe slug")
    return "ADV-" + created_on.replace("-", "") + "-" + slug


def duplicate_errors(candidate: dict, catalog: dict[str, dict]) -> list[str]:
    errors = []
    for key, record in catalog.items():
        if key == candidate["id"]:
            continue
        if normalized(key) == normalized(candidate["id"]):
            errors.append("NFKC+casefold ID collision: " + key)
        left, right = normalized(record["topic"]), normalized(candidate["topic"])
        if left == right:
            errors.append("duplicate topic: " + key)
        elif (SequenceMatcher(None, left, right).ratio() >= 0.82
              and not candidate["duplicate_reason"].strip()):
            errors.append("possible semantic duplicate (distinct reason required): " + key)
    return errors
