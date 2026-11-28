"""Replay main's registered debt at a report cutoff from saved Git evidence."""

from maintainability_lint.baseline import EXPECTED_KEYS

from .history_git import capture
from .period import parse_jst
from .quantities import measured

COUNTS = ("module_lines", "comment_blocks", "mixed_class_files")
PREFIX = "main_baseline_"
MAIN_FIRST_PARENT = "origin/main の first-parent コミット時刻からの事後復元"
DEFINITION = "期間観測上限より前の main の baseline 登録違反数"
BASIS_NOTE = "first-parent のコミット時刻を使う事後復元。GitHub への反映時刻は未観測です。"


def breakdown(record):
    if (not isinstance(record, dict) or set(record) != EXPECTED_KEYS
            or record["schema_version"] != 2 or not isinstance(record["source"], str)
            or not all(isinstance(record[key], dict) for key in COUNTS)):
        raise ValueError("baseline の版または構造が不正です")
    blocks = record["comment_blocks"].values()
    if any(type(value) is not int or value <= 0 for value in blocks):
        raise ValueError("baseline のコメント数が不正です")
    values = {"module_lines": len(record["module_lines"]), "comment_blocks": sum(blocks),
              "mixed_class_files": len(record["mixed_class_files"])}
    return {**values, "total": sum(values.values())}


def _initial(evidence):
    if evidence["shallow"]:
        return None, "shallow clone のため初期 baseline は確定できません"
    for commit in evidence["commits"]:
        version = evidence["versions"].get(commit["sha"])
        if version is None or version["absent"]:
            continue
        if version["reason"]:
            return None, version["reason"]
        try:
            counts = breakdown(version["record"])
        except ValueError as exc:
            return None, str(exc)
        return {**counts, "commit_sha": commit["sha"], "commit_at": commit["committed_at"]}, None
    return None, "baseline の導入コミットがありません"


def _at_cutoff(evidence, cutoff):
    current = version = None
    for commit in evidence["commits"]:
        if parse_jst(commit["effective_at"]) >= cutoff:
            break
        current = commit
        if current["sha"] in evidence["versions"]:
            version = current
    if current is None or version is None:
        return None, None, None, "観測上限より前の first-parent の履歴が確認できません"
    selected = evidence["versions"][version["sha"]]
    if selected["reason"]:
        return current, version, None, selected["reason"]
    try:
        return current, version, breakdown(selected["record"]), None
    except ValueError as exc:
        return current, version, None, str(exc)


def measure(evidence, cutoff):
    """Project the saved baseline as of a half-open event cutoff."""
    initial_reason = reason = evidence["reason"]
    current = version = values = initial = None
    if not reason:
        initial, initial_reason = _initial(evidence)
        current, version, values, reason = _at_cutoff(evidence, cutoff)
    details = {
        "main_sha": evidence["main_sha"], "commit_sha": current["sha"] if current else None,
        "commit_at": current["committed_at"] if current else None,
        "baseline_commit_sha": version["sha"] if version else None,
        "initial": initial, "initial_reason": initial_reason, "basis_note": BASIS_NOTE,
        "provenance": MAIN_FIRST_PARENT,
    }
    if initial and values:
        details["difference_from_initial"] = values["total"] - initial["total"]
    failed = evidence["reason"] or (version and not evidence["versions"][version["sha"]]["absent"]
                                    and evidence["versions"][version["sha"]]["reason"])
    return {PREFIX + key: measured(values[key] if values is not None else None,
                                    f"{DEFINITION}（{key}）", evidence["source"], reason=reason,
                                    status="not_retrieved" if failed else None,
                                    **(details if key == "total" else {}))
            for key in ("total", *COUNTS)}


def main_baseline(root, main_sha, cutoff):
    return measure(capture(root, main_sha), cutoff)
