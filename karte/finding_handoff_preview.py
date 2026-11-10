"""投稿予定の本文・確認トークン・警告を生成する。"""
import hashlib
import json
import re

from .errors import KarteUsageError
from .finding_handoff_block import render_block
from .finding_handoff_hash import content_hash

MAX_BODY_LENGTH = 65536


def digest(finding):
    try:
        return content_hash(finding.id, finding.harm, finding.summary, finding.locus, finding.expected)
    except (TypeError, ValueError) as exc:
        raise KarteUsageError(f"申し送り内容が不正です: {exc}") from exc


def preview(finding, target, agent):
    try:
        body = render_block(finding, agent)
    except (TypeError, ValueError) as exc:
        raise KarteUsageError(f"申し送り内容が不正です: {exc}") from exc
    if len(body) > MAX_BODY_LENGTH:
        raise KarteUsageError("本文が 65536 文字を超えます。申し送りを分けてください")
    data = json.dumps([body, target, agent, digest(finding)], ensure_ascii=False, separators=(",", ":"))
    return body, "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def has_mention(body):
    return bool(re.search(r"@[A-Za-z0-9][A-Za-z0-9-]*", body))
