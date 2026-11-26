"""Capture the local Karte subset without deriving historical dates or global counts."""

import re
import subprocess

from karte.errors import KarteNotFound
from karte.karte_loader import load_karte
from karte.format_error import KarteFormatError
from karte.paths import KarteMissing, KartePathError, karte_dir, main_worktree_root

from .git_source import read_git
from .quantities import measured

SOURCE = "主作業ツリーの tmp/_karte/issue-<N>.md"
SCOPE = "取得したローカルカルテのみ。リポジトリ全体の網羅性、レビュー実行日時、処置待ち開始日時は不明です。"
FILE = re.compile(r"issue-([1-9][0-9]*)\.md\Z")


def capture(root):
    evidence = {"source": SOURCE, "scope": SCOPE, "cards": [], "unreadable": [], "reason": None,
                "retrieved": False}
    try:
        primary = main_worktree_root(root)
        if primary != root.resolve():
            args = ("rev-parse", "--path-format=absolute", "--git-common-dir")
            if read_git(root, *args) != read_git(primary, *args):
                raise ValueError("karte worktree mismatch")
        candidates = sorted(karte_dir(primary).glob("issue-*.md"))
    except KarteMissing:
        return evidence | {"reason": "取得可能なローカルカルテの置き場がありません"}
    except (OSError, ValueError, KartePathError, subprocess.TimeoutExpired) as exc:
        return evidence | {"reason": f"ローカルカルテの置き場を読み取れません ({type(exc).__name__})"}
    evidence["retrieved"] = True
    for path in candidates:
        match = FILE.fullmatch(path.name)
        if match is None:
            continue
        try:
            issue = int(match[1])
            _, card = load_karte(primary, issue)
            if card.issue != issue:
                raise ValueError("karte issue mismatch")
            evidence["cards"].append({"issue": issue, "path": f"tmp/_karte/{path.name}", "findings": [
                {"id": finding.id, "harm": finding.harm, "status": finding.status,
                 "disposition": finding.disposition, "rounds": finding.rounds,
                 "resolved_round": finding.resolved_round, "owner_pending": finding.needs_disposition}
                for finding in card.findings
            ]})
        except (OSError, ValueError, KartePathError, KarteNotFound, KarteFormatError) as exc:
            evidence["unreadable"].append({"path": f"tmp/_karte/{path.name}", "reason": type(exc).__name__})
    if not evidence["cards"]:
        evidence["reason"] = "読み取れたローカルカルテがありません"
    return evidence


def measure(evidence):
    cards = evidence["cards"]
    findings = [item for card in cards for item in card["findings"]]
    real = [item for item in findings if item["harm"] == "real"]
    rounds = {(card["issue"], round_number) for card in cards for item in card["findings"]
               for round_number in item["rounds"] if round_number > 1 }
    stats = {
        "karte_observed_real_findings": (len(real), "採取できたローカルカルテに記録された実害指摘"),
        "karte_observed_open_real_findings": (sum(item["status"] == "open" for item in real),
                                            "採取時に open のローカルカルテ実害指摘"),
        "karte_observed_pending_disposition": (sum(item["owner_pending"] for item in real),
                                                "採取時にオーナーの処置方針を待つローカルカルテ実害指摘"),
        "karte_observed_rereview_rounds": (len(rounds), "指摘を記録したラウンド番号2以上の組（Issue・ラウンド）"),
    }
    return {key: measured(value if not evidence["reason"] else None, label, evidence["source"],
                          reason=evidence["reason"], scope=evidence["scope"],
                          status="not_retrieved" if not evidence["retrieved"] or
                          (not cards and evidence["unreadable"]) else None,
                          observed_karte_count=len(cards), observed_finding_count=len(findings),
                          unavailable_karte_count=len(evidence["unreadable"]))
            for key, (value, label) in stats.items()}
