"""Reconstruct historical state within the presently retrievable Issue cohort."""

from .gh_issue_history import event_time
from .quantities import measured

SCOPE = "現在の一覧から取得できた Issue に限定。削除・移管などで現在の一覧にない Issue は復元できません"


def restore_open(period, issues, transitions, timing):
    source = [issues["source"], transitions["source"]]
    definition = f"取得対象のうち集計上限の直前に開いていた Issue（収集後の状態遷移から復元、{timing}）"
    tags = {"observation_kind": "reconstructed", "scope": SCOPE}
    transfers = transitions.get("transfer_events")
    if transitions["rows"] is None or issues["rows"] is None:
        reason = transitions["reason"] or issues["reason"] or "対象時点までの状態履歴がありません"
    elif transfers is None:
        reason = "移管を確認できる履歴が保存されていません"
    elif transitions["history_start"] > period.cutoff:
        reason = "対象時点までの状態履歴がありません"
    else:
        return _from_history(period.cutoff, issues["rows"], transitions["rows"], transfers,
                             definition, source, tags)
    return measured(None, definition, source, reason=reason, **tags), None, None


def _from_history(cutoff, issues, transitions, transfers, definition, source, tags):
    active = {row["number"]: row for row in issues if row["created_at"] < cutoff}
    uncertain = {row["number"] for row in transfers
                 if row["created_at"] >= cutoff and row["number"] in active}
    known = {number: row for number, row in active.items() if number not in uncertain}
    opened = {number for number, row in known.items() if row["state"] == "open"}
    for row in reversed(transitions):
        number = row["number"]
        if event_time(row) >= cutoff and number in known:
            if row["event"] == "closed":
                opened.add(number)
            else:
                opened.discard(number)
    restored = [{"number": number, "title": known[number]["title"]} for number in sorted(opened)]
    if uncertain:
        reason = "集計上限以降の移管があり、上限直前の所属を確定できない Issue があります"
        return measured(None, definition, source, reason=reason, **tags, observed_count=len(restored),
                        uncertain_issue_numbers=sorted(uncertain)), None, restored
    return measured(len(restored), definition, source, **tags), restored, None
