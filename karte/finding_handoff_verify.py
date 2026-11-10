"""読み戻したコメントの投稿者と内容を照合する。"""

from .finding_handoff_block import parse_block
from .finding_handoff_hash import content_hash
from .finding_handoff_result import VerifyResult


def verify_comment(comment, finding, login):
    if not isinstance(comment, dict) or not isinstance(comment.get("user"), dict):
        return VerifyResult(False, "response_shape")
    author = comment["user"].get("login")
    if not isinstance(author, str) or not login or author.lower() != login.lower():
        return VerifyResult(False, "author")
    body = comment.get("body")
    parsed = parse_block(body) if isinstance(body, str) else None
    if parsed is None:
        return VerifyResult(False, "block")
    try:
        block_hash = content_hash(parsed["finding"], parsed["harm"], parsed["summary"],
                                  parsed["locus"], parsed["expected"])
        expected = content_hash(finding.id, finding.harm, finding.summary, finding.locus, finding.expected)
    except (TypeError, ValueError):
        return VerifyResult(False, "hash")
    return VerifyResult(block_hash == parsed["content_hash"] == expected,
                        "" if block_hash == parsed["content_hash"] == expected else "hash")
