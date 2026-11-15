"""Only link an existing GitHub issue: never create one automatically."""

import json
import os
import re
import urllib.error
import urllib.request

ISSUE = re.compile(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)#([1-9]\d*)\Z")


def verify_existing_issue(reference: str) -> None:
    match = ISSUE.fullmatch(reference)
    if not match:
        raise ValueError("expected existing issue owner/repo#number")
    owner, repo, number = match.groups()
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "review-system-advisory"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.load(response)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise ValueError("could not verify existing issue: " + str(exc)) from exc
    if (not isinstance(payload, dict) or "pull_request" in payload
            or payload.get("number") != int(number)
            or payload.get("repository_url", "").rstrip("/") !=
            f"https://api.github.com/repos/{owner}/{repo}"):
        raise ValueError("GitHub issue identity does not match")
