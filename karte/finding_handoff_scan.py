"""認証ユーザーが作成した既存の申し送りコメントを探す。"""

from .finding_handoff_block import parse_block


def scan_comments(comments, finding_id, digest, login):
    matches = []
    for comment in comments:
        user = comment.get("user")
        if not isinstance(user, dict) or not isinstance(user.get("login"), str):
            continue
        if not login or user["login"].lower() != login.lower():
            continue
        body = comment.get("body")
        block = parse_block(body) if isinstance(body, str) else None
        if block and block["finding"] == finding_id and block["content_hash"] == digest:
            matches.append(comment)
    matches.sort(key=lambda comment: comment["created_at"])
    return (matches[0], matches[1:]) if matches else (None, [])
