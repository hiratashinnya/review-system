"""GitHub の Issue 生成と stale 監査の境界。"""
import datetime
import json
import subprocess
import tempfile
from pathlib import Path


def run_gh(arguments, repo, runner=subprocess.run):
    result = runner(["gh", *arguments], cwd=repo, capture_output=True,
                    text=True, check=False, timeout=60)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "gh が失敗")
    return result.stdout.strip()


def issue_body(data):
    sections = ["Codex (AI) が ADR から生成しました。", f"ADR: {data['id']}"]
    for table in ("context", "decision"):
        for key, value in data[table].items():
            if key.startswith("tracking_") or key == "no_tracking_reason":
                continue
            sections.append(f"## {key}\n\n{value}")
    sections.append("## alternatives\n\n" + "\n".join(
        f"- {entry['option'].strip()}: {entry['rejection_reason'].strip()}"
        for entry in data["alternatives"]))
    return "\n\n".join(sections) + "\n"


def create_issue(data, repo, runner=subprocess.run):
    with tempfile.TemporaryDirectory(prefix="adr-issue-") as directory:
        body = Path(directory) / "body.md"
        body.write_text(issue_body(data), encoding="utf-8")
        url = run_gh(["issue", "create", "--title", data["topic"],
                      "--body-file", str(body)], repo, runner)
    import re
    match = re.fullmatch(r"https://github\.com/[^/]+/[^/]+/issues/([1-9][0-9]*)", url)
    if not match:
        raise ValueError(f"Issue作成結果のURLが不正、手動復旧が必要: {url}")
    return int(match.group(1)), url


def stale(records, repo, days, *, now=None, runner=subprocess.run):
    if days < 0:
        raise ValueError("days は0以上")
    now = now or datetime.datetime.now(datetime.timezone.utc)
    rows = []
    for data, _ in records:
        if data["decision"]["tracking_status"] != "filed":
            continue
        number = data["decision"]["tracking_issue"]
        issue = json.loads(run_gh(["issue", "view", str(number), "--json",
                                  "state,updatedAt,url"], repo, runner))
        updated = datetime.datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00"))
        if issue["state"] == "OPEN" and now - updated > datetime.timedelta(days=days):
            rows.append({"id": data["id"], "tracking_issue": number,
                         "updated_at": issue["updatedAt"], "url": issue["url"]})
    return rows
