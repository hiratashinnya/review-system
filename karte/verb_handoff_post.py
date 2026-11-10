"""確認済みの申し送りを投稿・読み戻し・記録する。"""
import hmac

from . import finding_handoff_context as context, finding_handoff_github as github
from .finding_handoff_errors import FindingHandoffError
from .finding_handoff_observe import comment_id, describe, timestamp, verify
from .finding_handoff_preview import digest, preview
from .finding_handoff_record import HandoffRecord
from .finding_handoff_scan import scan_comments
from .finding_handoff_store import snapshot, store
from .verb_boundary import fail_close


@fail_close(locked=False)
def cmd_handoff_post(args, repo_root, now=None):
    issue_id, karte = context.load(args, repo_root)
    finding = context.require_finding(karte, args.finding)
    target = context.target_for(finding, args.to, context.origin())
    body, token = preview(finding, target, args.agent)
    if not args.confirm or not hmac.compare_digest(args.confirm.encode("utf-8"), token.encode("utf-8")):
        raise FindingHandoffError("confirm", "確認トークンが無いか一致しません")
    observed, content = snapshot(finding), digest(finding)
    url = None
    try:
        issue = context.issue_status(target)
        login = github.current_login()
        found, duplicates = scan_comments(github.list_comments(target), finding.id, content, login)
        for duplicate in duplicates:
            print(f"重複ブロック: {duplicate['html_url']}")
        if found is None:
            if issue["locked"]:
                raise FindingHandoffError("locked", "宛先 Issue は locked で投稿できません")
            found = github.post_comment(target, body)
        url = found["html_url"]
        comment_id(target, url)
        verify(target, url, finding, login, content)
        record = HandoffRecord(target, url, content, timestamp(now), "verified")
        store(repo_root, issue_id, finding.id, observed, record)
    except FindingHandoffError as exc:
        if url:
            print(f"コメント URL: {url}")
        raise FindingHandoffError(exc.kind, describe(exc)) from exc
    print(f"検証済み: {url}")
    return 0
