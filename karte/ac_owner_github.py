"""The only sanctioned GitHub write adapter for automatic AC checks."""
import json
import re
import subprocess

from .errors import KarteUsageError

REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


def issue(repository, issue_number, *, new_body=None):
    """Read Issue or PATCH only its body; never operate on a pull request."""
    if not isinstance(repository, str) or not REPOSITORY.fullmatch(repository):
        raise KarteUsageError("GitHub repositoryはowner/name形式で指定する")
    endpoint = f"repos/{repository}/issues/{issue_number}"
    argv = ["gh", "api", endpoint]
    payload = None
    if new_body is not None:
        argv.extend(["--method", "PATCH", "--input", "-"])
        payload = json.dumps({"body": new_body}, ensure_ascii=False)
    try:
        response = subprocess.run(argv, input=payload, capture_output=True,
                                  text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise KarteUsageError(f"GitHub APIの実行に失敗: {exc}") from exc
    if response.returncode:
        raise KarteUsageError(f"GitHub APIが拒否: {response.stderr.strip()[:500]}")
    try:
        data = json.loads(response.stdout)
    except (ValueError, TypeError) as exc:
        raise KarteUsageError("GitHub Issue APIの応答がJSONでない") from exc
    if (not isinstance(data, dict) or type(data.get("number")) is not int
            or data["number"] != issue_number or "pull_request" in data
            or not isinstance(data.get("body"), str)):
        raise KarteUsageError("GitHub APIの対象Issueまたは本文が不正")
    return data["body"]
