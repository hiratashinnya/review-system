"""gh api 境界。gh 2.0 以上の -i 応答と Link ヘッダーを前提とする。

ページごとに -i でヘッダーと JSON を取得するため --paginate/--slurp は使わない。
実 gh での形式・最小版は未確認。
"""

import re

from .finding_handoff_errors import FindingHandoffError
from .finding_handoff_gh_run import run_json
from .finding_handoff_target import REPO


def _target(target):
    match = re.fullmatch(rf"({REPO})#([1-9][0-9]*)", target, re.ASCII)
    if not match:
        raise FindingHandoffError("response_shape", "不正な Issue 識別子")
    return match.group(1), int(match.group(2))


def _object(value, fields):
    if not isinstance(value, dict) or any(key not in value or not isinstance(value[key], typ)
                                          for key, typ in fields.items()):
        raise FindingHandoffError("response_shape", "gh api の応答形式が不正です")
    return value


def _comment(value):
    _object(value, {"body": str, "html_url": str, "created_at": str, "user": dict, "issue_url": str})
    _object(value["user"], {"login": str})
    return value


def _issue_url(repo, number):
    return f"https://api.github.com/repos/{repo}/issues/{number}"


def _same(actual, expected):
    if actual.lower() != expected.lower():
        raise FindingHandoffError("moved", "Issue が移転または改名されました")


def get_issue(target, run=None):
    repo, number = _target(target)
    _, value = run_json(["gh", "api", "-i", f"repos/{repo}/issues/{number}"], run)
    _object(value, {"state": str, "state_reason": (str, type(None)), "html_url": str,
                    "repository_url": str, "number": int, "locked": bool})
    if "pull_request" in value:
        raise FindingHandoffError("pull_request", "プルリクエスト宛には投稿できません")
    _same(value["html_url"], f"https://github.com/{repo}/issues/{number}")
    _same(value["repository_url"], f"https://api.github.com/repos/{repo}")
    if type(value["number"]) is not int or value["number"] != number:
        raise FindingHandoffError("moved", "Issue 番号が変わりました")
    return value


def list_comments(target, run=None):
    repo, number = _target(target)
    comments, page = [], 1
    while True:
        endpoint = f"repos/{repo}/issues/{number}/comments?per_page=100&page={page}"
        headers, values = run_json(["gh", "api", "-i", endpoint], run)
        if not isinstance(values, list):
            raise FindingHandoffError("response_shape", "コメント一覧の形式が不正です")
        for value in values:
            _comment(value)
            _same(value["issue_url"], _issue_url(repo, number))
        comments.extend(values)
        if not re.search(r'^link:\s*.*?;\s*rel="next"', headers, re.I | re.M):
            return comments
        page += 1


def get_comment(target, comment_id, run=None):
    repo, number = _target(target)
    if not re.fullmatch(r"[1-9][0-9]*", str(comment_id), re.ASCII):
        raise FindingHandoffError("response_shape", "不正なコメント番号")
    _, value = run_json(["gh", "api", "-i", f"repos/{repo}/issues/comments/{comment_id}"], run)
    _comment(value)
    _same(value["issue_url"], _issue_url(repo, number))
    return value


def post_comment(target, body, run=None):
    repo, number = _target(target)
    _, value = run_json(["gh", "api", "-i", f"repos/{repo}/issues/{number}/comments",
                         "-f", f"body={body}"], run)
    _comment(value)
    _same(value["issue_url"], _issue_url(repo, number))
    return value


def current_login(run=None):
    _, value = run_json(["gh", "api", "-i", "user"], run)
    _object(value, {"login": str})
    if not value["login"]:
        raise FindingHandoffError("response_shape", "login が空です")
    return value["login"]
