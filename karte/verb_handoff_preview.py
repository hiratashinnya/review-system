"""申し送り本文のプレビュー。"""
from . import finding_handoff_context as context
from .finding_handoff_preview import has_mention, preview
from .finding_handoff_errors import FindingHandoffError
from .finding_handoff_observe import describe
from .verb_boundary import fail_close


@fail_close(locked=False)
def cmd_handoff_preview(args, repo_root):
    _, karte = context.load(args, repo_root)
    finding = context.require_finding(karte, args.finding)
    target = context.target_for(finding, args.to, context.origin())
    body, token = preview(finding, target, args.agent)
    try:
        issue = context.issue_status(target)
    except FindingHandoffError as exc:
        raise FindingHandoffError(exc.kind, describe(exc)) from exc
    print(f"宛先: {target}\n{body}\n確認トークン: {token}")
    if issue["locked"]:
        print("警告: 宛先 Issue は locked です（既存ブロックの採用のみ可能）")
    if has_mention(body):
        print("警告: メンションによる通知が発生する可能性があります")
    return 0
