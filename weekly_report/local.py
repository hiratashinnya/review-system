"""Read-only observations from the worktree and existing ledgers."""

from collections import Counter
from dataclasses import asdict
from pathlib import Path
import subprocess
from typing import cast
from advisory.catalog import check_catalog, load_catalog
from advisory.paths import directory
from feedback_ledger.schema import PROPOSAL
from feedback_ledger.store import load_store
from maintainability_lint.baseline import load_baseline
from maintainability_lint.scanner import scan

from .period import parse_jst
from .quantities import measured


def _git(repo, *args):
    outcome = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), *args],
        check=False, capture_output=True, text=True, timeout=30,
    )
    if outcome.returncode:
        raise ValueError(f"git {args[0]} が失敗しました")
    return outcome.stdout.rstrip("\n")


def resolve_root(repo):
    return Path(_git(repo, "rev-parse", "--show-toplevel")).resolve()


def checkout(repo, base_ref):
    base_error = None
    try:
        base = _git(repo, "rev-parse", "--verify", "--end-of-options", base_ref + "^{commit}")
    except ValueError:
        base = None
        base_error = "指定 ref をローカルで解決できません"
    return {
        "base_ref": base_ref, "base_sha": base, "base_reason": base_error,
        "checkout_sha": _git(repo, "rev-parse", "--verify", "HEAD"),
        "checkout_dirty": bool(_git(repo, "status", "--porcelain=v1")),
    }


def maintainability(root):
    source = "maintainability_lint/baseline.json + maintainability_lint.scanner.scan"
    definition = "現在の作業ツリーで baseline と照合した保守性警告・違反"
    try:
        baseline = load_baseline(root / "maintainability_lint/baseline.json")
        result = scan(root, baseline)
        by_status = {status: dict(Counter(row.rule for row in result.findings if row.status == status))
                     for status in ("accepted-debt", "violation")}
        return measured(
            sum(by_status["violation"].values()), definition, source,
            baseline={"schema_version": baseline["schema_version"], "source": baseline["source"],
                      "module_lines": len(cast(dict, baseline["module_lines"])),
                      "comment_blocks": sum(cast(dict, baseline["comment_blocks"]).values()),
                      "mixed_class_files": len(cast(dict, baseline["mixed_class_files"]))},
            observed_by_status=by_status, findings=[asdict(row) for row in result.findings],
        )
    except (OSError, ValueError, SyntaxError, TypeError, AssertionError) as exc:
        return measured(None, definition, source, reason=f"スキャン不能 ({type(exc).__name__})")


def owner_proposals(root):
    source = ".ai/feedback/queue"
    definition = "フィードバック台帳で承認待ち (pending) の改訂案"
    try:
        if not (root / source).is_dir():
            raise ValueError("保管先がありません")
        store = load_store(root)
        if any(finding.level == "ERROR" for finding in store.findings):
            raise ValueError("台帳の検証に失敗しました")
        pending = [doc.relpath for doc in store.of(PROPOSAL) if doc.data["status"] == "pending"]
        return measured(len(pending), definition, source, proposals=pending)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        return measured(None, definition, source, reason=f"台帳を取得できません ({type(exc).__name__})")


def advisory(root, period):
    source = ".ai/advisory/ledger"
    definitions = {"advisories_created": "期間内に登録された Advisory",
                   "advisories_closed": "期間内に closed になった Advisory の遷移"}
    try:
        if not directory(root).is_dir():
            raise ValueError("台帳ディレクトリがありません")
        catalog = load_catalog(root)
        if check_catalog(catalog):
            raise ValueError("台帳の検証に失敗しました")
        events = [{"id": name, "topic": item["topic"], "event": event}
                  for name, item in catalog.items() for event in item["history"]
                  if period.contains(parse_jst(event["at"]))]
    except (OSError, ValueError, TypeError) as exc:
        return {key: measured(None, text, source, reason=f"台帳を取得できません ({exc})")
                for key, text in definitions.items()}
    selected = {"advisories_created": [row for row in events if row["event"]["action"] == "create"],
                "advisories_closed": [row for row in events if row["event"]["to_status"] == "closed" and row["event"]["from_status"] != "closed"]}
    return {key: measured(len(rows), definitions[key], source, events=rows) for key, rows in selected.items()}
