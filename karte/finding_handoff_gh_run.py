"""gh プロセスの実行と失敗の分類。"""

import json
import re
import subprocess

from .finding_handoff_errors import FindingHandoffError

GH_TIMEOUT = 30


def _text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _failure(error):
    output = (_text(error.stdout) + "\n" + _text(error.stderr)).lower()
    status = re.search(r"(?:http[/\d.]*\s+|http\s+|status[: ]+)(401|403|404|429|5\d\d)\b", output)
    code = int(status.group(1)) if status else 0
    if code == 429 or (code == 403 and (re.search(r"x-ratelimit-remaining\s*:\s*0\b|retry-after\s*:", output)
                                             or "rate limit" in output)):
        return "rate_limit"
    if code == 401 or "not logged" in output or "not logged in" in output or "gh auth login" in output:
        return "authentication"
    return {403: "permission", 404: "not_found"}.get(code, "server" if code >= 500 else "gh_failure")


def run_json(argv, run=None):
    run = run or subprocess.run
    try:
        result = run(argv, check=True, capture_output=True, text=True, timeout=GH_TIMEOUT, shell=False)
    except subprocess.CalledProcessError as exc:
        raise FindingHandoffError(_failure(exc), "gh api の実行に失敗しました") from exc
    except subprocess.TimeoutExpired as exc:
        raise FindingHandoffError("timeout", "gh api がタイムアウトしました") from exc
    except FileNotFoundError as exc:
        raise FindingHandoffError("gh_missing", "gh が見つかりません") from exc
    except OSError as exc:
        raise FindingHandoffError("gh_failure", "gh を実行できません") from exc
    except ValueError as exc:
        raise FindingHandoffError("invalid_json", "gh api の応答を解析できません") from exc
    try:
        raw = result.stdout.replace("\r\n", "\n")
        headers, body = raw.split("\n\n", 1)
        if not re.match(r"HTTP/\S+\s+\d{3}\b", headers):
            raise ValueError("missing HTTP headers")
        return headers, json.loads(body)
    except (AttributeError, TypeError, ValueError) as exc:
        raise FindingHandoffError("invalid_json", "gh api の応答を解析できません") from exc
