"""投稿予定の本文・確認トークン・警告を生成する。"""
import hashlib
import json
import re

from .errors import KarteUsageError
from .finding_handoff_block import parse_block, render_block
from .finding_handoff_hash import content_hash

MAX_BODY_LENGTH = 65536


ROUND_TRIP_FIELDS = ("finding", "harm", "summary", "locus", "expected")
ROUND_TRIP_MESSAGE = ("申し送り内容が不正です: 転記ブロックの書式に使われる文字列を含むなどで"
                      "本文が往復できません。指摘の文面を直して再実行してください")


def digest(finding):
    try:
        return content_hash(finding.id, finding.harm, finding.summary, finding.locus, finding.expected)
    except (TypeError, ValueError) as exc:
        raise KarteUsageError(f"申し送り内容が不正です: {exc}") from exc


def require_round_trip(body, expected_digest):
    parsed = parse_block(body)
    if parsed is None:
        raise KarteUsageError(ROUND_TRIP_MESSAGE)
    if not parsed["content_hash"] == content_hash(*(parsed[key] for key in ROUND_TRIP_FIELDS)) == expected_digest:
        raise KarteUsageError(ROUND_TRIP_MESSAGE)


def preview(finding, target, agent):
    try:
        body = render_block(finding, agent)
    except (TypeError, ValueError) as exc:
        raise KarteUsageError(f"申し送り内容が不正です: {exc}") from exc
    if len(body) > MAX_BODY_LENGTH:
        raise KarteUsageError("本文が 65536 文字を超えます。申し送りを分けてください")
    expected_digest = digest(finding)
    require_round_trip(body, expected_digest)
    data = json.dumps([body, target, agent, expected_digest], ensure_ascii=False, separators=(",", ":"))
    return body, "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def has_mention(body):
    return bool(re.search(r"@[A-Za-z0-9][A-Za-z0-9-]*", body))
