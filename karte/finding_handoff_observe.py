"""コメントの読み戻し・投稿者・内容の照合。"""
import re
from datetime import datetime, timezone

from . import finding_handoff_github as github
from .finding_handoff_errors import FindingHandoffError
from .finding_handoff_verify import verify_comment


def comment_id(target, url):
    repo, number = target.rsplit("#", 1)
    match = re.fullmatch(rf"https://github\.com/{re.escape(repo)}/issues/{number}#issuecomment-([1-9][0-9]*)",
                         url, re.IGNORECASE | re.ASCII)
    if not match:
        raise FindingHandoffError("comment_url", "コメント URL が宛先と一致しません")
    return match.group(1)


def verify(target, url, finding, login, expected_hash):
    from .finding_handoff_preview import digest
    if digest(finding) != expected_hash:
        raise FindingHandoffError("hash", "finding のハッシュが記録と一致しません")
    comment = github.get_comment(target, comment_id(target, url))
    if comment["html_url"].lower() != url.lower():
        raise FindingHandoffError("moved", "コメント URL が変わりました")
    result = verify_comment(comment, finding, login)
    if not result.valid:
        raise FindingHandoffError(result.reason, f"コメントの照合に失敗しました: {result.reason}")


def timestamp(now=None):
    value = now if now is not None else datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now は timezone を持つ必要があります")
    return value.astimezone(timezone.utc).isoformat()


def describe(error):
    hint = {"rate_limit": "待って再実行してください", "authentication": "gh auth status と権限を確認してください",
            "permission": "gh auth status と権限を確認してください"}.get(error.kind, "")
    return f"{error.kind}: {error} {hint}".rstrip()
