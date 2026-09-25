"""``python3 -m ci_anomaly_report`` entrypoint。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .collector import GitHubAPI, collect_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect main-branch CI anomalies")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        parser.error("GH_TOKEN or GITHUB_TOKEN is required")
    api = GitHubAPI(token, api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    report = collect_report(api.get, args.repository, branch=args.branch)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0
